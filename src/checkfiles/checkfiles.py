import argparse
import datetime
import gzip
import hashlib
import json
import logging
import math
import multiprocessing
import os
import re
import requests
import shlex
import shutil
import subprocess
import sys
import time
import tempfile

import pyfastx
import pysam

from collections import namedtuple
from typing import Optional

from FastaValidator import fasta_validator

from frictionless import system
from frictionless import validate

import file

import logformatter


SCHEMA_DIR = 'src/schemas/'
CHROM_INFO_DIR = SCHEMA_DIR + 'genome_builds'
MAX_NUM_ERROR_FOR_TABULAR_FILE = 10

ZIP_FILE_FORMAT = [
    'bam',
    'fastq',
    'txt',
    'tsv',
    'bed',
    'bedpe',
    'fasta',
    'gtf'
]

TABULAR_FORMAT = [
    'txt',
    'tsv',
]

TABULAR_FILE_SCHEMAS = {
    'element quantifications': 'src/schemas/table_schemas/element_quant.json'
}

VALIDATE_FILES_ARGS = {
    ('bed', 'bed3'): ['-type=bed3'],
    ('bed', 'CRISPR element quantifications'): ['-type=bed3+22', '-as=src/schemas/file_formats/as/element_quant_format.as'],
    ('bed', 'bed3+'): ['-tab', '-type=bed3+'],
    ('bed', 'bedGraph'): ['-type=bedGraph'],
    ('bedpe', None): ['-type=bed3+'],
    ('bigBed', 'bed3'): ['-type=bigBed3'],
    ('bigBed', 'bed3+'): ['-tab', '-type=bigBed3+'],
    ('bigWig', None): ['-type=bigWig'],
    ('bigInteract', None): ['-type=bigBed5+13', '-as=src/schemas/file_formats/as/interact.as'],

}

HUMAN_ASSEMBLIES = ['GRCh38', 'hg19']

RODENT_ASSEMBLIES = ['GRCm39', 'GRCm38', 'MGSCv37']


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


def file_validation(portal_url, portal_auth: PortalAuth, validation_record: file.FileValidationRecord, submitted_md5sum, output_type, file_format_type, assembly):
    uuid = validation_record.uuid
    logger.info(f'Checking file uuid {uuid}')
    local_file_path = validation_record.file.path
    try:
        true_file_size_bytes = validation_record.file.size
        validation_record.update_info({'file_size': true_file_size_bytes})
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
    validation_record.update_info(
        {'md5sum': validation_record.file.md5sum})
    logger.info(f'{uuid} md5sum is {validation_record.file.md5sum}')
    md5_sum_error = check_md5sum(
        submitted_md5sum, validation_record.file.md5sum)
    validation_record.update_errors(md5_sum_error)
    if is_gzipped:
        content_md5_error = check_content_md5sum(
            validation_record.file.content_md5sum, portal_auth, portal_url)
        validation_record.update_info(
            {'content_md5sum': validation_record.file.content_md5sum})
        logger.info(
            f'{uuid} content_md5sum is {validation_record.file.content_md5sum}')
        validation_record.update_errors(content_md5_error)
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
            output_type, local_file_path)
        validation_record.update_errors(tabular_file_check_error)
    logger.info(
        f'Completed file validation for file uuid {uuid}.')

    if validation_record.errors:
        validation_record.validation_success = False
        return validation_record
    else:
        validation_record.validation_success = True
        return validation_record


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
            'md5sum': f'submitted file md5sum {expected_md5sum} does not match calculated md5sum {calculated_md5sum}.'}
    return error


def check_content_md5sum(content_md5sum, portal_auth: Optional[PortalAuth] = None, portal_url=None):
    error = {}
    url = portal_url + '/search/?type=File&format=json&content_md5sum=' + content_md5sum
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
            info = {'bam_number_of_reads': count}
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
        # mean might not be an integer to begin with, but schema wants integer so floor it
        info.update({split_item[0]: math.floor(float(split_item[1]))})
    return info


def fasta_check(file_path, is_gzipped, info=FASTA_VALIDATION_INFO):
    error = {}
    if is_gzipped:
        with gzip.open(file_path, 'rb') as f_in:
            temp_file = tempfile.NamedTemporaryFile()
            with open(temp_file.name, 'wb') as f_out:
                temp_file = tempfile.NamedTemporaryFile()
                shutil.copyfileobj(f_in, f_out)
        file_path = temp_file.name
    try:
        code = fasta_validator(file_path)
        if code != 0:
            error['fasta_error'] = info[code]
    except Exception as e:
        error['fasta_error'] = str(e)
    return error


def tabular_file_check(output_type, file_path, schemas=TABULAR_FILE_SCHEMAS, max_error=MAX_NUM_ERROR_FOR_TABULAR_FILE):
    system.trusted = True
    error = {}
    schema_path = schemas.get(output_type)
    report = validate(file_path, schema=schema_path)
    if not report.valid:
        report = report.flatten(['rowNumber', 'fieldNumber', 'type', 'note'])
        if len(report) > max_error:
            report = report[0:max_error]
        error = {
            'tabular_file_error': report
        }
    return error


def validate_files_check(file_path, file_format, file_format_type, assembly):
    error = {}
    chrom_info_file = get_chrom_info_file(assembly)

    validate_args = get_validate_files_args(
        file_format, file_format_type, chrom_info_file)
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


def get_validate_files_args(file_format, file_format_type, chrom_info_file, schema=VALIDATE_FILES_ARGS):
    args = schema.get((file_format, file_format_type))
    chrom_info_arg = 'chromInfo=' + chrom_info_file
    args.append(chrom_info_arg)
    return args


def get_chrom_info_file(assembly, chrom_info_dir=CHROM_INFO_DIR):
    if assembly in HUMAN_ASSEMBLIES:
        organism = 'human'
    elif assembly in RODENT_ASSEMBLIES:
        organism = 'rodent'
    return f'{chrom_info_dir}/{organism}/{assembly}/chrom.sizes'


def fetch_file_metadata_by_uuid(uuid: str, server: str, portal_auth: PortalAuth):
    response = requests.get(server + '/' + uuid, auth=portal_auth)
    # todo handle exceptions, retries etc.
    return response.json()


def make_local_path_from_s3_uri(s3_uri: str):
    return re.sub(r's3://', '/', s3_uri)


def get_file_validation_record_from_metadata(file_metadata: dict, mount_basedir=os.environ.get('HOME')):
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
        search = f'search?type=File&upload_status=pending&field=uuid&field=upload_status&field=md5sum&field=file_format&field=file_format_type&field=s3_uri&field=assembly&field=output_type&limit={number_of_files}'
    else:
        search = 'search?type=File&upload_status=pending&field=uuid&field=upload_status&field=md5sum&field=file_format&field=file_format_type&field=s3_uri&field=assembly&field=output_type&limit=all'
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
    return file_validation(*job)


def patching_worker(job):
    portal_uri = job[0]
    portal_auth = job[1]
    file_validation_record = job[2]
    current_uuid = file_validation_record.uuid
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
            output_type = file_metadata.get('output_type')
            file_format_type = file_metadata.get('file_format_type')
            submitted_md5sum = file_metadata['md5sum']
            file_validation_record = get_file_validation_record_from_metadata(
                file_metadata)
            etag_original = fetch_etag_for_uuid(
                args.server, args.uuid, portal_auth)
            file_validation_record.original_etag = etag_original
            file_validation_complete_record = file_validation(args.server, portal_auth, file_validation_record,
                                                              submitted_md5sum, output_type, file_format_type, assembly=assembly)
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
                credentials_expired = upload_credentials_are_expired(
                    args.server, uuid, portal_auth)
                if not credentials_expired:
                    logger.info(
                        'Upload credentials for {uuid} not expired yet, skipping check.')
                    continue
                assembly = file_metadata.get('assembly')
                output_type = file_metadata.get('output_type')
                file_format_type = file_metadata.get('file_format_type')
                submitted_md5sum = file_metadata['md5sum']
                file_validation_record = get_file_validation_record_from_metadata(
                    file_metadata)
                etag_original = fetch_etag_for_uuid(
                    args.server, uuid, portal_auth)
                file_validation_record.original_etag = etag_original
                jobs.append((args.server, portal_auth, file_validation_record,
                            submitted_md5sum, output_type, file_format_type, assembly))
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
