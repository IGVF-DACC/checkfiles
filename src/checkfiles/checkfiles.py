import argparse
import datetime
import gzip
import json
import logging
from math import floor
import multiprocessing
import os
import re
import requests
import shlex
import shutil
import subprocess
import sys
import tempfile

import pysam

from collections import namedtuple
from typing import Optional

from FastaValidator import fasta_validator
from frictionless import system, validate, describe, Schema, Dialect
from seqspec.utils import load_spec as seqspec_load_spec
from seqspec.seqspec_check import run_check as seqspec_check


from guide_rna_sequences_check import GuideRnaSequencesCheck
import file
from version import get_checkfiles_version

import logformatter


SCHEMA_DIR = 'src/schemas/'
CHROM_INFO_DIR = SCHEMA_DIR + 'genome_builds'
MAX_NUM_ERROR_FOR_TABULAR_FILE = 1000
MAX_NUM_DETAILED_ERROR_FOR_TABULAR_FILE = 2
ASSEMBLY_REPORT_FILE_PATH = {
    # this file is downloaded here:https://ftp.ncbi.nlm.nih.gov/genomes/all/GCF/000/001/405/GCF_000001405.40_GRCh38.p14/GCF_000001405.40_GRCh38.p14_assembly_report.txt
    'GRCh38': 'src/checkfiles/supporting_files/GCF_000001405.40_GRCh38.p14_assembly_report.txt',
    # this file is downloaded here: https://ftp.ncbi.nlm.nih.gov/genomes/all/GCF/000/001/635/GCF_000001635.27_GRCm39/GCF_000001635.27_GRCm39_assembly_report.txt
    'GRCm39': 'src/checkfiles/supporting_files/GCF_000001635.27_GRCm39_assembly_report.txt',
}
ZIP_FILE_FORMAT = [
    'bam',
    'bed',
    'bedpe',
    'csfasta',
    'csqual',
    'csv',
    'dat',
    'fasta',
    'fastq',
    'gaf',
    'gds',
    'gff',
    'gtf',
    'mtx',
    'obo',
    'owl',
    'tagAlign',
    'tar',
    'tbi',
    'tsv',
    'txt',
    'vcf',
    'wig',
    'xml',
    'yaml',
]

NO_HEADER_CONTENT_TYPE = [
    'fragments'
]
TABULAR_FORMAT = [
    'tsv',
    'csv',
]

TABULAR_FILE_SCHEMAS = {
    'guide RNA sequences': 'src/schemas/table_schemas/guide_rna_sequences.json',
    'MPRA sequence designs': 'src/schemas/table_schemas/mpra_sequence_designs.json',
    'prime editing guide RNA sequences': 'src/schemas/table_schemas/prime_editing_guide_rna_sequences.json',
}

VALIDATE_FILES_ARGS = {
    ('bed', 'bed3'): ['-type=bed3'],
    ('bed', 'bed3+'): ['-tab', '-type=bed3+'],
    ('bed', 'bed5'): ['-type=bed5'],
    ('bed', 'bed6'): ['-type=bed6'],
    ('bed', 'bed6+'): ['-tab', '-type=bed6+'],
    ('bed', 'bed9'): ['-type=bed9'],
    ('bed', 'bed9+'): ['-tab', '-type=bed9+'],
    ('bed', 'bed12'): ['-type=bed12'],
    ('bed', 'bedGraph'): ['-type=bedGraph'],
    ('bed', 'mpra_starr'): ['-type=bed6+5', '-as=src/schemas/as/mpra_starr.as'],
    ('bedpe', None): ['-type=bed3+'],
    ('bigBed', 'bed3'): ['-type=bigBed3'],
    ('bigBed', 'bed3+'): ['-tab', '-type=bigBed3+'],
    ('bigWig', None): ['-type=bigWig'],
    ('bigInteract', None): ['-type=bigBed5+13', '-as=src/schemas/as/interact.as'],

}

ASSEMBLY_TO_CHROMINFO_PATH_MAP = {
    'GRCh38': 'src/schemas/genome_builds/chrom_sizes/GRCh38.chrom.sizes',
    'GRCm39': 'src/schemas/genome_builds/chrom_sizes/mm39.chrom.sizes',
}

ASSEMBLY = ['GRCh38', 'GRCm39']

ASSEMBLY_TO_SEQUENCE_FILE_MAP = {
    'GRCh38': 'src/checkfiles/supporting_files/grch38.fa',
    'GRCm39': 'src/checkfiles/supporting_files/grcm39.fa',
}

FASTA_VALIDATION_INFO = {
    0: 'this is a valid fasta file',
    1: 'the first line does not start with a > (rule 1 violated).',
    2: 'there are duplicate sequence identifiers in the file (rule 7 violated)',
    4: 'there are characters in a sequence line other than [A-Za-z]'
}


PortalAuth = namedtuple('PortalAuth', ['portal_key_id', 'portal_secret_key'])


logger = logging.getLogger(__name__)
handler = logging.StreamHandler()
handler.setFormatter(logformatter.JsonFormatter())
logger.addHandler(handler)
logger.setLevel(logging.INFO)


def file_validation(portal_url, portal_auth: PortalAuth, validation_record: file.FileValidationRecord, submitted_md5sum, content_type, file_format_type, assembly, validate_onlist_files=True):
    uuid = validation_record.uuid
    logger.info(f'Checking file uuid {uuid}')
    local_file_path = validation_record.file.path
    validation_record.update_info(
        {'checkfiles_version': get_checkfiles_version()})
    try:
        true_file_size_bytes = validation_record.file.size
        validation_record.update_info({'file_size': true_file_size_bytes})
        if true_file_size_bytes == 0:
            validation_record.update_errors(
                {'file_size': 'file has zero size'})
            return validation_record
    except FileNotFoundError:
        logger.warning(f'File not found for {uuid}')
        validation_record.file_not_found = True
        return validation_record
    logger.info(f'{uuid} file size {true_file_size_bytes} bytes')
    file_format = validation_record.file.file_format
    is_gzipped = validation_record.file.is_zipped
    gzipped_format_error = check_valid_gzipped_file_format(
        is_gzipped, file_format)
    validation_record.update_errors(gzipped_format_error)
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
                validation_record.file.content_md5sum, uuid, portal_auth, portal_url)
            validation_record.update_info(
                {'content_md5sum': validation_record.file.content_md5sum})
            logger.info(
                f'{uuid} content_md5sum is {validation_record.file.content_md5sum}')
            validation_record.update_errors(content_md5_error)
        except EOFError as e:
            logger.warning(
                f'{uuid} the gzipped file is corrupted.'
            )
            validation_record.update_errors(
                {'file_content_error': 'EOFError: Compressed file ended before the end-of-stream marker was reached'}
            )
            return validation_record
    if file_format == 'bam':
        bam_check_result = bam_pysam_check(local_file_path)
        if 'bam_error' in bam_check_result:
            validation_record.update_errors(bam_check_result)
        else:
            validation_record.update_info(bam_check_result)
    elif file_format == 'fastq':
        validate_files_fastq_check_error = validate_files_fastq_check(
            local_file_path)
        validation_record.update_errors(validate_files_fastq_check_error)
        fastq_read_info = fastq_get_average_read_length_and_number_of_reads(
            local_file_path)
        validation_record.update_info(fastq_read_info)
    elif file_format in ['bed', 'bigWig', 'bigInteract', 'bigBed', 'bedpe']:
        validate_files_check_error = validate_files_check(
            local_file_path, file_format, file_format_type, assembly)
        validation_record.update_errors(validate_files_check_error)
    elif file_format == 'fasta':
        fasta_check_error = fasta_check(local_file_path, is_gzipped)
        validation_record.update_errors(fasta_check_error)
    elif file_format in TABULAR_FORMAT:
        tabular_file_check_error = tabular_file_check(
            content_type, local_file_path, is_gzipped)
        validation_record.update_errors(tabular_file_check_error)
    elif file_format == 'vcf':
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
        return validation_record
    else:
        validation_record.validation_success = True
        return validation_record


def get_header_row(file_path, is_gzipped):
    # right now we assume there is only one header row and header row should not be started with '#
    count = 0
    open_func = gzip.open if is_gzipped else open
    with open_func(file_path, 'rt', encoding='utf-8') as f:
        for line in f:
            if line.startswith('#'):
                count += 1
            else:
                break

    return count + 1


def check_valid_gzipped_file_format(is_gzipped, file_format, zip_file_format=ZIP_FILE_FORMAT):
    error = {}
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


def bam_pysam_check(file_path):
    try:
        pysam.quickcheck(file_path)
        result = pysam.stats(file_path)
        if 'SN\tis sorted:\t0' in result:
            error = {'bam_error': 'the bam file is not sorted'}
            return error
        else:
            samfile = pysam.AlignmentFile(file_path, 'rb')
            count = samfile.count(until_eof=True)
            logger.info(f'the number of reads: {count}')
            info = {'read_count': count}
            samfile.close()
            return info
    except pysam.utils.SamtoolsError as e:
        error = {
            'bam_error': f'file is not valid bam file by SamtoolsError: {str(e)}'}
        return error


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


def tabular_file_check(content_type, file_path, is_gzipped, schemas=TABULAR_FILE_SCHEMAS, max_error=MAX_NUM_ERROR_FOR_TABULAR_FILE, allow_additional_fields=True, schema_path=None):
    system.trusted = True
    error = {}
    if content_type not in NO_HEADER_CONTENT_TYPE:
        header_row = get_header_row(file_path, is_gzipped)
        dialect = Dialect(comment_char='#', header_rows=[header_row])
    else:
        dialect = Dialect(header=False, comment_char='#')
    if not schema_path:
        schema_path = schemas.get(content_type)
    if not schema_path:
        # if no schema, we can ignore type-error
        report = validate(file_path, limit_errors=max_error,
                          skip_errors=['type-error'], dialect=dialect)
    else:
        checks = []
        if content_type in ['guide RNA sequences', 'prime editing guide RNA sequences']:
            checks = [GuideRnaSequencesCheck()]
        if not allow_additional_fields:
            report = validate(file_path, schema=schema_path,
                              limit_errors=max_error, checks=checks, dialect=dialect)
        else:
            infer_schema = describe(file_path, type='schema', dialect=dialect)
            schema = Schema.from_descriptor(schema_path)
            if len(infer_schema.fields) > len(schema.fields):
                for i in range(len(schema.fields), len(infer_schema.fields)):
                    schema.add_field(infer_schema.fields[i])
            report = validate(file_path, schema=schema,
                              limit_errors=max_error, checks=checks, dialect=dialect)

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
    if assembly not in ASSEMBLY:
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
        if validate_onlist_files:
            errors = seqspec_check(file_path, None, 'igvf')
        else:
            errors = seqspec_check(file_path, None, 'igvf_onlist_skip')
        if errors:
            error['seqspec_error'] = errors
    except Exception as e:
        error['seqspec_error'] = str(e)
        logger.exception(
            f'exception occurred when checking seqspec yaml file: {str(e)}')
    return error


def get_validate_files_args(file_format, file_format_type, chrom_info_file, schema=VALIDATE_FILES_ARGS):
    args = schema[(file_format, file_format_type)]
    chrom_info_arg = 'chromInfo=' + chrom_info_file
    args.append(chrom_info_arg)
    return args


def validate_files_check(file_path, file_format, file_format_type, assembly, chrominfo_file_paths=ASSEMBLY_TO_CHROMINFO_PATH_MAP):
    error = {}
    try:
        chrom_info_file_path = chrominfo_file_paths[assembly]
    except KeyError:
        error_message = f'{assembly} is not a valid assembly. Valid assemblies: {list(chrominfo_file_paths.keys())}'
        error['validate_files'] = error_message
        return error
    try:
        validate_args = get_validate_files_args(
            file_format, file_format_type, chrom_info_file_path)
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
        search = f'search?type=File&upload_status=pending&field=uuid&field=upload_status&field=md5sum&field=file_format&field=file_format_type&field=s3_uri&field=assembly&field=content_type&field=validate_onlist_files&limit={number_of_files}'
    else:
        search = 'search?type=File&upload_status=pending&field=uuid&field=upload_status&field=md5sum&field=file_format&field=file_format_type&field=s3_uri&field=assembly&field=content_type&field=validate_onlist_files&limit=all'
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
            validate_onlist_files = file_metadata.get('validate_onlist_files')
            submitted_md5sum = file_metadata['md5sum']
            file_validation_record = get_file_validation_record_from_metadata(
                file_metadata)
            etag_original = fetch_etag_for_uuid(
                args.server, args.uuid, portal_auth)
            file_validation_record.original_etag = etag_original
            file_validation_complete_record = file_validation(args.server, portal_auth, file_validation_record,
                                                              submitted_md5sum, content_type, file_format_type, assembly, validate_onlist_files)
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
                validate_onlist_files = file_metadata.get(
                    'validate_onlist_files')
                submitted_md5sum = file_metadata['md5sum']
                file_validation_record = get_file_validation_record_from_metadata(
                    file_metadata)
                etag_original = fetch_etag_for_uuid(
                    args.server, uuid, portal_auth)
                file_validation_record.original_etag = etag_original
                jobs.append((args.ignore_active_credentials, args.server, portal_auth, file_validation_record,
                            submitted_md5sum, content_type, file_format_type, assembly, validate_onlist_files))
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
