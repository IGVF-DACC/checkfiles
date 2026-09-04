import argparse
import datetime
import gzip
import h5py
from io import BytesIO
import json
import logging
import multiprocessing
import os
import re
import requests
import shlex
import shutil
import subprocess
import sys
import tempfile
import zlib

from collections import namedtuple
from math import floor
from typing import Optional

import pysam
from FastaValidator import fasta_validator
from frictionless import system, validate, describe, Schema, Dialect
from frictionless.exception import FrictionlessException
from seqspec.utils import load_spec as seqspec_load_spec
from seqspec.seqspec_version import seqspec_version
from seqspec.seqspec_check import seqspec_check

import file
import logformatter
from constants import MAX_NUM_ERROR_FOR_TABULAR_FILE, UTF_8_ENCODING
from constants import MAX_NUM_DETAILED_ERROR_FOR_TABULAR_FILE, ASSEMBLY_REPORT_FILE_PATH, ZIP_FILE_FORMAT
from constants import GZIP_CHECK_IGNORED_FILE_FORMAT, NO_HEADER_CONTENT_TYPE, TABULAR_FORMAT, TABULAR_FILE_SCHEMAS
from constants import VALIDATE_FILES_ARGS, ASSEMBLY_TO_CHROMINFO_PATH_MAP, ASSEMBLY_FOR_VCF, ASSEMBLY_TO_SEQUENCE_FILE_MAP
from constants import FASTA_VALIDATION_INFO, SEQSPEC_FILE_VERSION, NO_SQ_HEADER_BAM_CONTENT_TYPES
from guide_rna_sequences_check import GuideRnaSequencesCheck
from regulator_check import RegulatorCheck
from version import get_checkfiles_version


PortalAuth = namedtuple('PortalAuth', ['portal_key_id', 'portal_secret_key'])


logger = logging.getLogger(__name__)
handler = logging.StreamHandler()
handler.setFormatter(logformatter.JsonFormatter())
logger.addHandler(handler)
logger.setLevel(logging.INFO)


def file_validation(portal_url, portal_auth: PortalAuth, validation_record: file.FileValidationRecord, submitted_md5sum, content_type, file_format_type, assembly, reference_files, validate_onlist_files=True):
    uuid = validation_record.uuid
    logger.info(f'Checking file uuid {uuid}')
    local_file_path = validation_record.file.path
    validation_record.update_info(
        {
            'checkfiles_version': get_checkfiles_version(),
            'checkfiles_timestamp': get_current_utc_time().isoformat()
        }
    )
    try:
        true_file_size_bytes = validation_record.file.size
        validation_record.update_info({'file_size': true_file_size_bytes})
        if true_file_size_bytes == 0:
            validation_record.update_errors(
                {'file_size': 'file has zero size'})
            validation_record.validation_success = False
            logger.info(
                f'Completed file validation for file uuid {uuid}. Upload status: {validation_record.upload_status}')
            return validation_record
    except FileNotFoundError:
        logger.warning(f'File not found for {uuid}')
        validation_record.file_not_found = True
        logger.info(
            f'Completed file validation for file uuid {uuid}. Upload status: {validation_record.upload_status}')
        return validation_record
    logger.info(f'{uuid} file size {true_file_size_bytes} bytes')
    file_format = validation_record.file.file_format
    is_gzipped = validation_record.file.is_zipped
    gzipped_format_error = check_valid_gzipped_file_format(
        is_gzipped, file_format)
    if gzipped_format_error:
        validation_record.update_errors(gzipped_format_error)
        validation_record.validation_success = False
        logger.info(
            f'Completed file validation for file uuid {uuid}. Upload status: {validation_record.upload_status}')
        return validation_record
    logger.info(f'{uuid} calculated md5sum is {validation_record.file.md5sum}')
    md5_sum_error = check_md5sum(
        submitted_md5sum, validation_record.file.md5sum)
    validation_record.update_errors(md5_sum_error)
    if md5_sum_error:
        logger.info(
            f'{uuid} calculated md5sum {validation_record.file.md5sum} does not match submitted md5sum {submitted_md5sum}')
    if is_gzipped:
        try:
            content_md5_error = check_content_md5sum(
                validation_record.content_md5sum, uuid, portal_auth, portal_url)
            validation_record.update_info(
                {'content_md5sum': validation_record.content_md5sum})
            logger.info(
                f'{uuid} content_md5sum is {validation_record.content_md5sum}')
            validation_record.update_errors(content_md5_error)
        except (EOFError, zlib.error, gzip.BadGzipFile) as e:
            logger.error(
                f'{uuid} the gzipped file is corrupted: {str(e)}',
                exc_info=True
            )
            validation_record.update_errors(
                {'file_content_error': f'{str(e)}'}
            )
            validation_record.validation_success = False
            logger.info(
                f'Completed file validation for file uuid {uuid}. Upload status: {validation_record.upload_status}')
            return validation_record
    if file_format == 'bam':
        bam_check_result = bam_pysam_check(local_file_path, content_type)
        if 'bam_error' in bam_check_result:
            validation_record.update_errors(bam_check_result)
        else:
            validation_record.update_info(bam_check_result)
    elif file_format == 'cram':
        if not reference_files:
            logger.warning(
                f'{uuid} the cram file is missing reference files.')
            validation_record.update_errors(
                {'cram_error': 'the cram file is missing reference files.'})
        else:
            reference_file_path = get_reference_file_path(
                reference_files[0], portal_url, portal_auth)
            cram_check_result = cram_pysam_check(
                local_file_path, reference_file_path)
            if 'cram_error' in cram_check_result:
                validation_record.update_errors(cram_check_result)
            else:
                validation_record.update_info(cram_check_result)
    elif file_format == 'fastq':
        validate_files_fastq_check_error = validate_files_fastq_check(
            local_file_path)
        validation_record.update_errors(validate_files_fastq_check_error)
        fastq_read_info = fastq_get_average_read_length_and_number_of_reads(
            local_file_path)
        validation_record.update_info(fastq_read_info)
    elif file_format in ['bed', 'bigWig', 'bigInteract', 'bigBed', 'bedpe']:
        validate_files_check_error = validate_files_check(
            local_file_path, file_format, file_format_type, assembly, content_type)
        validation_record.update_errors(validate_files_check_error)
    elif file_format == 'fasta':
        fasta_check_error = fasta_check(local_file_path, is_gzipped)
        validation_record.update_errors(fasta_check_error)
    elif file_format == 'h5ad':
        h5ad_check_error = check_valid_h5ad_file_format(local_file_path)
        validation_record.update_errors(h5ad_check_error)
    elif file_format in TABULAR_FORMAT:
        tabular_file_check_error = tabular_file_check(
            file_format, content_type, local_file_path)
        validation_record.update_errors(tabular_file_check_error)
    elif file_format in ['vcf', 'gvcf']:
        vcf_check_error = vcf_sequence_check(local_file_path, assembly)
        validation_record.update_errors(vcf_check_error)
    elif content_type == 'seqspec':
        seqspec_check_error = seqspec_file_check(
            local_file_path, validate_onlist_files)
        validation_record.update_errors(seqspec_check_error)

    logger.info(
        f'Completed file validation for file uuid {uuid}.')

    if validation_record.errors:
        validation_record.validation_success = False
    else:
        validation_record.validation_success = True
    logger.info(
        f'Completed file validation for file uuid {uuid}. Upload status: {validation_record.upload_status}')
    return validation_record


def get_header_row(file_path, is_gzipped, encoding=UTF_8_ENCODING):
    """Count leading # comment lines and return 1-based header row number. Right now we assume there is only one header row and header row should not be started with '#'"""
    count = 0
    open_func = gzip.open if is_gzipped else open
    with open_func(file_path, 'rt', encoding=encoding) as f:
        for line in f:
            if line.lstrip().startswith('#'):
                count += 1
            else:
                break
    return count + 1


def check_valid_h5ad_file_format(file_path):
    error = {}
    try:
        with h5py.File(file_path, 'r') as f:
            if not all(group in f for group in ['X', 'obs', 'var']):
                error = {
                    'h5ad_error': 'Missing one or more required anndata groups X, obs and var. This appears to be a generic h5 file.'}
    except Exception as e:
        error = {
            'h5ad_error': f'Exception checking h5ad file format: {str(e)}'}
    return error


def check_valid_gzipped_file_format(is_gzipped, file_format, zip_file_format=ZIP_FILE_FORMAT):
    error = {}
    if file_format in GZIP_CHECK_IGNORED_FILE_FORMAT:
        return error
    if file_format in zip_file_format and not is_gzipped:
        error = {'gzip': f'{file_format} file should be gzipped'}
    elif file_format not in zip_file_format and is_gzipped:
        error = {'gzip': f'{file_format} file should not be gzipped'}
    return error


def check_md5sum(expected_md5sum, calculated_md5sum):
    error = {}
    if expected_md5sum != calculated_md5sum:
        error = {
            'md5sum': f'original md5sum {expected_md5sum} does not match newly calculated md5sum {calculated_md5sum}.'}
    return error


def make_content_md5sum_search_url(content_md5sum, uuid, portal_url):
    search_url = f'{portal_url}/search/?type=File&format=json&status!=replaced&status!=deleted&uuid!={uuid}&content_md5sum={content_md5sum}'
    logger.info(f'content_md5sum search url: {search_url}')
    return search_url


def check_content_md5sum(content_md5sum, uuid, portal_auth: Optional[PortalAuth] = None, portal_url=None):
    error = {}
    url = make_content_md5sum_search_url(content_md5sum, uuid, portal_url)
    session = requests.Session()
    session.auth = portal_auth
    conflict_files = session.get(url).json()['@graph']
    if conflict_files:
        accessions = []
        for file in conflict_files:
            accessions.append(file['accession'])
        accessions_serialize = ', '.join(accessions)
        error = {
            'content_md5sum_error': f'content md5sum {content_md5sum} conflicts with content md5sum of existing file(s): {accessions_serialize}'
        }
    return error


def bam_pysam_check(file_path, content_type, no_sq_header_bam_content_types=NO_SQ_HEADER_BAM_CONTENT_TYPES):
    try:
        if content_type not in no_sq_header_bam_content_types:
            pysam.quickcheck(file_path)
        result = pysam.stats(file_path)
        if 'SN\tis sorted:\t0' in result:
            error = {'bam_error': f'the bam file is not sorted'}
            return error
        else:
            with pysam.AlignmentFile(file_path, 'rb', check_sq=False) as samfile:
                if not samfile.header:
                    error = {'bam_error': f'the bam file has invalid header'}
                    return error
                count = samfile.count(until_eof=True)
                logger.info(f'the number of reads: {count}')
                info = {'read_count': count}
                return info
    except pysam.utils.SamtoolsError as e:
        error = {
            'bam_error': f'file is not valid bam file by SamtoolsError: {str(e)}'}
        return error


def get_reference_file_path(reference_file, portal_url, portal_auth):
    # reference_file looks like this: /reference-files/TSTFI36924773/
    search_url = f'{portal_url}{reference_file}'
    session = requests.Session()
    session.auth = portal_auth
    metadata = session.get(search_url).json()
    reference_file_path = os.environ.get(
        'HOME') + make_local_path_from_s3_uri(metadata['s3_uri'])
    return reference_file_path


def is_zipped(file_path):
    try:
        gzip.GzipFile(filename=file_path).read(1)
        return True
    except gzip.BadGzipFile:
        return False


def cram_pysam_check(file_path, reference_file_path):
    info = {}
    # unzip the reference file to a temporary file using tempfile if reference_file_path is gzipped
    gzipped = is_zipped(reference_file_path)
    if gzipped:
        temp_file = tempfile.NamedTemporaryFile(
            delete=False)  # Prevent auto-delete
        with gzip.open(reference_file_path, 'rb') as f_in:
            with open(temp_file.name, 'wb') as f_out:
                shutil.copyfileobj(f_in, f_out)
        reference_file_path = temp_file.name
    try:
        pysam.quickcheck(file_path)

        # First command: samtools view
        view_cmd = shlex.split(
            f'samtools view -h -T {reference_file_path} {file_path}')

        # Second command: samtools stats -
        stats_cmd = shlex.split('samtools stats -')

        with subprocess.Popen(view_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE) as p1:
            with subprocess.Popen(stats_cmd, stdin=p1.stdout, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True) as p2:
                p1.stdout.close()  # Let p1 receive SIGPIPE if p2 exits
                _, err_view = p1.communicate()  # Capture stderr from view
                if err_view:
                    info = {'cram_error': f'samtools view error: {err_view}'}
                else:
                    output, err_stats = p2.communicate()
                    if err_stats:
                        info = {
                            'cram_error': f'samtools stats error: {err_stats}'}
                    else:
                        if 'SN\tis sorted:\t0' in output:
                            info = {'cram_error': f'the cram file is not sorted'}
                        else:
                            with pysam.AlignmentFile(file_path, 'rc', reference_filename=reference_file_path) as cram:
                                count = cram.count(until_eof=True)
                                logger.info(f'the number of reads: {count}')
                                info = {'read_count': count}

    except pysam.utils.SamtoolsError as e:
        info = {
            'cram_error': f'file is not valid cram file by SamtoolsError: {str(e)}'}
    except subprocess.CalledProcessError as e:
        info['cram_error'] = f'Subprocess error ({e.cmd}): {e.stderr.strip()}'
    finally:
        if gzipped:
            temp_file.close()
            os.unlink(temp_file.name)  # Manually remove the file
    return info


def fastq_get_average_read_length_and_number_of_reads(file_path):
    command = shlex.split(f'fastq_stats {file_path}')
    try:
        output = subprocess.check_output(command)
    except subprocess.CalledProcessError as e:
        message = f'error when calculating stats for fastq in {file_path}: {str(e)}'
        logger.exception(message)
        # checker should have updated error by this point
        return {}
    info = {}
    # b'read_count: 41437223\nminimum_read_length: 28\nmaximum_read_length: 28\nmean_read_length: 28\n' is what output looks like
    for item in output.decode().strip().split('\n'):
        split_item = item.split(': ')
        # should floor read_count, minimum_read_length and maximum_read_length. Round the mean_read_length
        if split_item[0] == 'mean_read_length':
            info.update({split_item[0]: round(float(split_item[1]), 2)})
        else:
            info.update({split_item[0]: floor(float(split_item[1]))})

    return info


def fasta_check(file_path, is_gzipped, info=FASTA_VALIDATION_INFO):
    error = {}
    temp_file = tempfile.NamedTemporaryFile(
        delete=False)  # Prevent auto-delete
    if is_gzipped:
        with gzip.open(file_path, 'rb') as f_in:
            with open(temp_file.name, 'wb') as f_out:
                shutil.copyfileobj(f_in, f_out)
        file_path = temp_file.name
    try:
        code = fasta_validator(file_path)
        if code != 0:
            error['fasta_error'] = info[code]
    except Exception as e:
        error['fasta_error'] = str(e)
    finally:
        temp_file.close()  # Close before deleting
        os.unlink(temp_file.name)  # Manually remove the file
    return error


def tabular_file_check(file_format, content_type, file_path, is_gzipped=True, schemas=TABULAR_FILE_SCHEMAS, max_error=MAX_NUM_ERROR_FOR_TABULAR_FILE, allow_additional_fields=True, schema_path=None):
    try:
        system.trusted = True
        error = {}
        # Build minimal dialect with comment_char and header_rows.
        if content_type not in NO_HEADER_CONTENT_TYPE:
            header_row = get_header_row(
                file_path, is_gzipped)
            dialect = Dialect(comment_char='#', header_rows=[header_row])
        else:
            dialect = Dialect(header=False, comment_char='#')

        # When file is gzipped but filename lacks .gz, frictionless won't auto-detect compression.
        # Pass compression='gz' when the file is gzipped and force UTF-8.
        frictionless_options = {
            'dialect': dialect,
            'format': file_format,
            'encoding': UTF_8_ENCODING
        }
        if is_gzipped:
            frictionless_options['compression'] = 'gz'
        if not schema_path:
            schema_path = schemas.get(content_type)
        if not schema_path:
            # if no schema, we can ignore type-error
            report = validate(file_path, limit_errors=max_error,
                              skip_errors=['type-error'], **frictionless_options)
        else:
            checks = []
            # handle barcode to sample mapping separately
            if content_type == 'barcode to sample mapping':
                infer_schema = describe(
                    file_path, type='schema', **frictionless_options)
                if len(infer_schema.fields) not in [6, 3]:
                    error = {
                        'tabular_file_error': f'barcode to sample mapping file should have 6 or 3 columns, but found {len(infer_schema.fields)} columns'
                    }
                    return error
                if len(infer_schema.fields) == 6:
                    schema_path = schema_path[0]
                else:
                    schema_path = schema_path[1]
                report = validate(file_path, schema=schema_path,
                                  limit_errors=max_error, checks=checks, **frictionless_options)
            else:

                if content_type in ['guide RNA sequences', 'prime editing guide RNA sequences']:
                    checks = [GuideRnaSequencesCheck()]
                elif content_type in [
                    'regulator-regulator correlation',
                    'gene program regulators',
                ]:
                    checks = [RegulatorCheck()]

                if not allow_additional_fields:
                    report = validate(file_path, schema=schema_path,
                                      limit_errors=max_error, checks=checks, **frictionless_options)
                else:
                    infer_schema = describe(
                        file_path, type='schema', **frictionless_options)
                    schema = Schema.from_descriptor(schema_path)
                    if len(infer_schema.fields) > len(schema.fields):
                        for i in range(len(schema.fields), len(infer_schema.fields)):
                            schema.add_field(infer_schema.fields[i])
                    report = validate(file_path, schema=schema,
                                      limit_errors=max_error, checks=checks, **frictionless_options)
    except (UnicodeDecodeError, FrictionlessException) as e:
        logger.error(
            f'exception occurred when checking tabular file: {str(e)}')
        return {
            'tabular_file_error': f'exception occurred when checking tabular file: {str(e)}'
        }
    if not report.valid:
        report = report.flatten(
            ['rowNumber', 'fieldNumber', 'type', 'note', 'description'])
        number_of_errors = len(report)
        error_types = list(set([row[2] for row in report]))
        tabular_file_error = {
            'schema': schema_path,
            'error_number_limit': max_error,
            'number_of_errors': number_of_errors,
        }
        for row in report:
            error_type = row[2]
            if error_type in tabular_file_error:
                tabular_file_error[error_type]['count'] += 1
                if len(tabular_file_error[error_type]['details']) < MAX_NUM_DETAILED_ERROR_FOR_TABULAR_FILE:
                    tabular_file_error[error_type]['details'].append(
                        {
                            'row_number': row[0],
                            'field_number': row[1],
                            'note': row[3],
                        }
                    )
            else:
                tabular_file_error[error_type] = {}
                tabular_file_error[error_type]['count'] = 1
                tabular_file_error[error_type]['description'] = row[4]
                tabular_file_error[error_type]['details'] = [
                    {
                        'row_number': row[0],
                        'field_number': row[1],
                        'note': row[3],
                    }
                ]

        tabular_file_error['error_types'] = error_types
        error = {
            'tabular_file_error': tabular_file_error,
        }

    return error


def vcf_sequence_check(file_path, assembly):
    error = {}
    if assembly not in ASSEMBLY_FOR_VCF:
        error['vcf_error'] = f'assembly {assembly} is not supported.'
        return error
    ref_file_path = ASSEMBLY_TO_SEQUENCE_FILE_MAP[assembly]
    # check vcf file
    command = ['vcf_assembly_checker',
               '-i', file_path, '-f', ref_file_path, '-a', ASSEMBLY_REPORT_FILE_PATH[assembly]]
    try:
        subprocess.check_output(
            command, stderr=subprocess.STDOUT)
    except subprocess.CalledProcessError as e:
        error['vcf_error'] = e.output.decode(
            errors='replace').rstrip('\n')
    return error


def seqspec_file_check(file_path, validate_onlist_files=True):
    error = {}
    # check if IGVF_API_KEY and IGVF_SECRET_KEY are set
    if 'IGVF_API_KEY' not in os.environ or 'IGVF_SECRET_KEY' not in os.environ:
        logger.warning(
            f'IGVF_API_KEY and IGVF_SECRET_KEY are not set. seqspec check will not be able to access files that are not released.')
    try:
        spec = seqspec_load_spec(file_path)
        version = seqspec_version(spec)['file_version']
        if version != SEQSPEC_FILE_VERSION:
            error['seqspec_error'] = f'The seqspec file version is {version}, while version {SEQSPEC_FILE_VERSION} is required.'
            return error
        if validate_onlist_files:
            errors = seqspec_check(spec, file_path, 'igvf')
        else:
            errors = seqspec_check(spec, file_path, 'igvf_onlist_skip')
        if errors:
            error['seqspec_error'] = errors
    except Exception as e:
        error['seqspec_error'] = str(e)
        logger.exception(
            f'exception occurred when checking seqspec yaml file: {str(e)}')
    return error


def get_validate_files_args(file_format, file_format_type, chrom_info_file, content_type=None, schema=VALIDATE_FILES_ARGS):
    # bedpe files do not have file_format_type; select schema by content_type.
    if file_format == 'bedpe' and content_type == 'element to gene interactions':
        args = list(schema[(file_format, content_type)])
    else:
        args = list(schema[(file_format, file_format_type)])
    chrom_info_arg = 'chromInfo=' + chrom_info_file
    args.append(chrom_info_arg)
    return args


def validate_files_check(file_path, file_format, file_format_type, assembly, content_type=None, chrominfo_file_paths=ASSEMBLY_TO_CHROMINFO_PATH_MAP):
    error = {}
    if assembly not in ASSEMBLY_TO_CHROMINFO_PATH_MAP.keys():
        error['validate_files'] = f'assembly {assembly} is not supported. Valid assemblies: {ASSEMBLY_TO_CHROMINFO_PATH_MAP.keys()}'
        return error
    chrom_info_file_path = chrominfo_file_paths[assembly]
    try:
        validate_args = get_validate_files_args(
            file_format, file_format_type, chrom_info_file_path, content_type)
    except KeyError:
        error_message = f'file_format: {file_format} file_format_type: {file_format_type} combination not allowed.'
        error['validate_files'] = error_message
        return error
    command = ['validateFiles'] + validate_args + [file_path]
    try:
        output = subprocess.check_output(command, stderr=subprocess.STDOUT)
    except subprocess.CalledProcessError as e:
        error['validate_files'] = e.output.decode(
            errors='replace').rstrip('\n')
    return error


def validate_files_fastq_check(file_path):
    error = {}
    command = ['validateFiles'] + ['-type=fastq'] + [file_path]
    try:
        output = subprocess.check_output(command, stderr=subprocess.STDOUT)
    except subprocess.CalledProcessError as e:
        error['validate_files'] = e.output.decode(
            errors='replace').rstrip('\n')
    return error


def fetch_file_metadata_by_uuid(uuid: str, server: str, portal_auth: PortalAuth):
    response = requests.get(server + '/' + uuid, auth=portal_auth)
    # todo handle exceptions, retries etc.
    return response.json()


def make_local_path_from_s3_uri(s3_uri: str):
    return re.sub(r's3://', '/', s3_uri)


def get_file_validation_record_from_metadata(file_metadata: dict, mount_basedir=os.environ.get('HOME')):
    if mount_basedir is None:
        mount_basedir = '/home/ubuntu'
    if not ('s3_uri' in file_metadata and 'file_format' in file_metadata and 'uuid' in file_metadata):
        raise ValueError('Invalid metadata dict')
    else:
        path = mount_basedir + \
            make_local_path_from_s3_uri(file_metadata['s3_uri'])
        uuid = file_metadata['uuid']
        file_format = file_metadata['file_format']
        return file.FileValidationRecord(file.get_file(path, file_format), uuid)


def get_current_utc_time():
    return datetime.datetime.now(tz=datetime.timezone.utc)


def upload_credentials_are_expired(portal_uri: str, file_uuid: str, portal_auth: PortalAuth) -> bool:
    logger.info(
        f'Checking upload credential expiration status for {file_uuid}')
    request_uri = f'{portal_uri}/{file_uuid}/@@upload'
    response = requests.get(request_uri, auth=portal_auth)
    expiration = response.json(
    )['@graph'][0]['upload_credentials']['expiration']
    # portal times are utc
    expiration_time = datetime.datetime.fromisoformat(expiration)
    now = get_current_utc_time()
    return expiration_time < now


def fetch_pending_files_metadata(portal_uri: str, portal_auth: PortalAuth, number_of_files: Optional[int] = None) -> list:
    if number_of_files is not None:
        search = f'search?type=File&upload_status=pending&field=uuid&field=upload_status&field=md5sum&field=file_format&field=file_format_type&field=s3_uri&field=assembly&field=content_type&field=validate_onlist_files&field=reference_files&limit={number_of_files}'
    else:
        search = 'search?type=File&upload_status=pending&field=uuid&field=upload_status&field=md5sum&field=file_format&field=file_format_type&field=s3_uri&field=assembly&field=content_type&field=validate_onlist_files&field=reference_files&limit=all'
    search_uri = f'{portal_uri}/{search}'
    response = requests.get(search_uri, auth=portal_auth)
    metadata = response.json()['@graph']
    return metadata


def fetch_etag_for_uuid(portal_uri: str, file_uuid: str, portal_auth: PortalAuth) -> str:
    request_uri = f'{portal_uri}/{file_uuid}?frame=edit&datastore=database'
    etag_response = requests.get(request_uri, auth=portal_auth)
    etag = etag_response.headers['etag']
    return etag


def worker(job):
    # throw away the active credential info, since we are not patching it does not matter
    _, *job = job
    return file_validation(*job)


def patching_worker(job):
    ignore_active_credentials, *job = job
    portal_uri = job[0]
    portal_auth = job[1]
    file_validation_record = job[2]
    current_uuid = file_validation_record.uuid
    credentials_expired = upload_credentials_are_expired(
        portal_uri, current_uuid, portal_auth)
    if not credentials_expired and not ignore_active_credentials:
        logger.info(
            f'Upload credentials for {current_uuid} are not expired yet. Skipping.')
        return
    if not credentials_expired and ignore_active_credentials:
        logger.info(
            f'Upload credentials for {current_uuid} are not expired yet and ignore_active_credentials is set, proceeding to patch.')
    result = file_validation(*job)
    original_etag = file_validation_record.original_etag
    etag_after = fetch_etag_for_uuid(portal_uri, current_uuid, portal_auth)
    if not etag_after == original_etag:
        logger.warning(
            f'etag original {original_etag} does not match etag after validation {etag_after}. Will not patch {current_uuid}.')
        return
    else:
        logger.info(
            f'etag original {original_etag} matches etag after validation {etag_after}. Will patch {current_uuid}.')
        patch_response = patch_file(portal_uri, portal_auth, result)
        logger.info(f'Attempted patching {current_uuid}. patch response:')
        logger.info(json.dumps(patch_response))
        return patch_response


def patch_file(portal_uri: str, portal_auth: PortalAuth, validation_record: file.FileValidationRecord) -> dict:
    headers = {
        'accept': 'application/json',
        'Content-Type': 'application/json'
    }
    uuid_to_patch = validation_record.uuid
    payload = validation_record.make_payload()
    logger.info(f'Patching {uuid_to_patch} on {portal_uri}')
    response = requests.patch(
        f'{portal_uri}/{uuid_to_patch}', data=payload, headers=headers, auth=portal_auth)
    return response.json()


def main(args):
    portal_auth = PortalAuth(args.portal_key_id, args.portal_secret_key)
    os.environ['IGVF_API_KEY'] = args.portal_key_id
    os.environ['IGVF_SECRET_KEY'] = args.portal_secret_key
    if args.uuid:
        try:
            file_metadata = fetch_file_metadata_by_uuid(
                args.uuid, args.server, portal_auth)
            uuid = args.uuid
            credentials_expired = upload_credentials_are_expired(
                args.server, uuid, portal_auth)

            if not args.ignore_active_credentials:
                if not credentials_expired:
                    logger.info(
                        'Upload credentials for {args.uuid} are not expired yet. Skipping.')
                    return
            else:
                logger.warning('Skipping upload credentials expired check')
            assembly = file_metadata.get('assembly')
            content_type = file_metadata.get('content_type')
            file_format_type = file_metadata.get('file_format_type')
            validate_onlist_files = file_metadata.get(
                'validate_onlist_files', True)
            submitted_md5sum = file_metadata['md5sum']
            reference_files = file_metadata.get('reference_files')
            file_validation_record = get_file_validation_record_from_metadata(
                file_metadata)
            etag_original = fetch_etag_for_uuid(
                args.server, args.uuid, portal_auth)
            file_validation_record.original_etag = etag_original
            file_validation_complete_record = file_validation(portal_url=args.server, portal_auth=portal_auth, validation_record=file_validation_record,
                                                              submitted_md5sum=submitted_md5sum, content_type=content_type, file_format_type=file_format_type, assembly=assembly, reference_files=reference_files, validate_onlist_files=validate_onlist_files)
            if args.patch:
                # check etag first
                etag_after = fetch_etag_for_uuid(
                    args.server, args.uuid, portal_auth)
                if not etag_after == file_validation_complete_record.original_etag:
                    logger.warning(
                        f'etag original {etag_original} does not match etag after validation {etag_after}. Will not patch {args.uuid}.')
                    return
                else:
                    logger.info(
                        f'etag original {etag_original} matches etag after validation {etag_after}. Will patch {args.uuid}.')
                    patch_response = patch_file(
                        args.server, portal_auth, file_validation_complete_record)
                    print(json.dumps(patch_response))
        except Exception as err:
            message = f'exception occurred when checking file uuid {args.uuid}: {str(err)}'
            logger.exception(message)
            sys.exit(1)  # Retry Job Task by exiting the process
    else:
        try:
            pending_files = fetch_pending_files_metadata(
                args.server, portal_auth, args.number_of_files)
            if not pending_files:
                logger.info('No files in pending state found. Exiting.')
                return
            jobs = []
            for file_metadata in pending_files:
                uuid = file_metadata['uuid']
                assembly = file_metadata.get('assembly')
                content_type = file_metadata.get('content_type')
                file_format_type = file_metadata.get('file_format_type')
                reference_files = file_metadata.get('reference_files')
                validate_onlist_files = file_metadata.get(
                    'validate_onlist_files', True)
                submitted_md5sum = file_metadata['md5sum']
                file_validation_record = get_file_validation_record_from_metadata(
                    file_metadata)
                etag_original = fetch_etag_for_uuid(
                    args.server, uuid, portal_auth)
                file_validation_record.original_etag = etag_original
                jobs.append((args.ignore_active_credentials, args.server, portal_auth, file_validation_record,
                            submitted_md5sum, content_type, file_format_type, assembly, reference_files, validate_onlist_files))
            number_of_cpus = multiprocessing.cpu_count()

            if args.patch:
                with multiprocessing.Pool(number_of_cpus) as pool:
                    results = pool.map(patching_worker, jobs)
            else:
                with multiprocessing.Pool(number_of_cpus) as pool:
                    results = pool.map(worker, jobs)

            print('Validation finished')
        except Exception as e:
            logger.exception('Validation failed')
            raise e


# Start script
if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Checkfiles argumentparser')
    parser.add_argument('--uuid', type=str,
                        help='UUID of the fileobject to be checked.')
    parser.add_argument(
        '--server', type=str, help='igvf instance to check. https://api.sandbox.igvf.org for example')
    parser.add_argument('--portal-key-id', type=str, help='Portal key id')
    parser.add_argument('--portal-secret-key', type=str,
                        help='Portal secret key')
    parser.add_argument('--patch', action='store_true',
                        help='Patch the checked objects.')
    parser.add_argument('--number-of-files', type=str,
                        help='Use this option to limit the number of pending files to check. If unset, all the pending files will be checked.')
    parser.add_argument('--ignore-active-credentials', action='store_true',
                        help='If this flag is set, then we omit checking if the file has unexpired upload credentials. There be dragons here, someone might change the underlying file after checking.')

    args = parser.parse_args()
    main(args)
