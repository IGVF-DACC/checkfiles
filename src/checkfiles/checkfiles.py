import json
import requests
import hashlib
import gzip
import pysam
import pyfastx
import json
import os
import sys
import logging
import boto3
import shutil
import tempfile
from frictionless import validate
from frictionless import system

# some files for test: ENCFF594AYI.fastq.gz, ENCFF206HGF.bam, ENCFF080HPN.tsv, ENCFF500IBL.tsv
BUCKET_NAME = os.getenv('BUCKET_NAME', 'checkfiles-test')
KEY = os.getenv(
    'KEY', '2022/10/31/8b19341b-b1b2-4e10-ad7f-aa910ccd4d2c/ENCFF500IBL.tsv')
MD5SUM = os.getenv('MD5SUM', '3e814f4af7a4c13460584b26fbe32dc')
FILE_FORMAT = os.getenv('FILE_FORMAT', 'tsv')
OUTPUT_TYPE = os.getenv('OUTPUT_TYPE', 'element quantifications')
UUID = os.getenv('UUID', '462bd56-9278-48aa-bc55-9eff587ba2c7')
FILE_SIZE = os.getenv('FILE_SIZE', 137)
NUMBER_OF_READS = os.getenv('NUMBER_OF_READS', 2)
READ_LENGTH = os.getenv('READ_LENGTH', 5)
ENCODE_ACCESS_KEY = os.getenv('ENCODE_ACCESS_KEY', '')
ENCODE_SECRET_KEY = os.getenv('ENCODE_SECRET_KEY', '')
DATA_DIR = '/s3/'
CHUNK_SIZE = 128*6400
MAX_NUM_ERROR_FOR_TABULAR_FILE = 10

ZIP_FILE_FORMAT = [
    'bam',
    'fastq',
    'txt',
    'tsv',
]

TABULAR_FORMAT = [
    'txt',
    'tsv',
]

EXCLUDE_FORMAT = [
    'bai',
]

TABULAR_FILE_SCHEMAS = {
    'element quantifications': 'src/schemas/table_schemas/element_quant.json'
}

CONTENT_MD5SUM_URL = 'https://www.encodeproject.org/search/?type=File&format=json&content_md5sum='

logging.basicConfig(
    format='%(asctime)s | %(levelname)s: %(message)s', level=logging.INFO)


def main():
    try:
        response = file_validation(BUCKET_NAME, KEY, UUID,
                                   MD5SUM, FILE_FORMAT, OUTPUT_TYPE, FILE_SIZE, NUMBER_OF_READS, READ_LENGTH)
        logging.info(json.dumps(response))
    except Exception as err:
        message = f'exception occurred when checking file uuid #{UUID}: {str(err)}'

        logging.info(json.dumps({'exception': message}))
        sys.exit(1)  # Retry Job Task by exiting the process


def file_validation(bucket_name, key, uuid, md5sum, file_format, output_type, file_size, number_of_reads, read_length):
    logging.info(f'Checking file uuid {uuid}...')
    response = boto3.client('s3').get_object(Bucket=bucket_name, Key=key)
    file_path = get_local_file_path(key)

    errors = {}
    is_gzipped = is_file_gzipped(file_path)
    logging.info(f'is file gziped: {is_gzipped}')
    error = check_valid_gzipped_file_format(is_gzipped, file_format)
    errors.update(error)
    error = check_file_size(file_size, response.get('ContentLength'))
    errors.update(error)
    error = check_md5sum(md5sum, response.get('ETag').strip('"'), file_path)
    errors.update(error)

    if is_gzipped:
        error = check_content_md5sum(file_path)
        errors.update(error)

    if file_format == 'bam':
        error = bam_pysam_check(file_path, number_of_reads)
        errors.update(error)
        if 'bam_error' not in errors:
            bam_generate_bai_file(file_path)
    elif file_format == 'fastq':
        error = fastq_check(file_path, number_of_reads, read_length)
        errors.update(error)
    elif file_format in TABULAR_FORMAT:
        error = tabular_file_check(output_type, file_path)
        errors.update(error)
    logging.info(f'Completed file validation for file uuid {uuid}.')

    if errors:
        return {
            'uuid': uuid,
            'validation_result': 'failed',
            'errors': errors
        }
    else:
        return {
            'uuid': uuid,
            'validation_result': 'pass'
        }


def get_local_file_path(key):
    file_path = DATA_DIR + key
    return file_path


def is_file_gzipped(file_path):
    try:
        gzip.GzipFile(filename=file_path).read(1)
        return True
    except gzip.BadGzipFile:
        return False


def check_valid_gzipped_file_format(is_gzipped, file_format, zip_file_format=ZIP_FILE_FORMAT):
    error = {}
    if file_format in zip_file_format and not is_gzipped:
        error = {'gzip': f'{file_format} file should be gzipped'}
    elif file_format not in zip_file_format and is_gzipped:
        error = {'gzip': f'{file_format} file should not be gzipped'}
    return error


def check_file_size(file_size, size_in_cloud_storage):
    error = {}
    if size_in_cloud_storage != file_size:
        error = {
            'file_size': f'submitted file zise {str(file_size)} does not mactch file zise {str(size_in_cloud_storage)} in cloud storage'}
    return error


def check_md5sum(md5sum, etag, file_path, chunk_size=CHUNK_SIZE):
    error = {}
    logging.info(f'the eTag is {etag}')
    if etag != md5sum:
        md5 = hashlib.md5()
        with open(file_path, 'rb') as local_file:
            while chunk := local_file.read(chunk_size):
                md5.update(chunk)
        calculated_md5sum = md5.hexdigest()

        if md5sum != calculated_md5sum:
            error = {
                'md5sum': f'submitted file md5sum {md5sum} does not mactch file md5sum {calculated_md5sum} in cloud storage'}
    return error


def check_content_md5sum(file_path, chunk_size=CHUNK_SIZE, base_url=CONTENT_MD5SUM_URL, username=ENCODE_ACCESS_KEY, password=ENCODE_SECRET_KEY):
    error = {}
    md5 = hashlib.md5()
    with gzip.open(file_path) as f:
        while chunk := f.read(chunk_size):
            md5.update(chunk)
    content_md5sum = md5.hexdigest()
    logging.info(f'content md5sum is {content_md5sum}')
    url = base_url + content_md5sum
    session = requests.Session()
    session.auth = (username, password)
    conflict_files = session.get(url).json()['@graph']
    if conflict_files:
        accessions = []
        for file in conflict_files:
            accessions.append(file['accession'])
        error = {
            'content_md5sum': f"content md5sum {content_md5sum} conflicts with content md5sum of existing file(s): {', '.join(accessions)}"}
    return error


def bam_pysam_check(file_path, number_of_reads):
    error = {}
    try:
        pysam.quickcheck(file_path)
        result = pysam.stats(file_path)
        if 'SN\tis sorted:\t0' in result:
            error = {'bam_error': 'the bam file is not sorted'}
        else:
            samfile = pysam.AlignmentFile(file_path, 'rb')
            count = samfile.count(until_eof=True)
            logging.info(f'the number of reads: {count}')
            if count != number_of_reads:
                error = {
                    'bam_error': f'sumbitted number of reads {number_of_reads} does not match number of reads {count} in cloud storage'}
            samfile.close()
    except pysam.utils.SamtoolsError as e:
        error = {
            'bam_error': f'file is not valid bam file by SamtoolsError: {str(e)}'}
    return error


def bam_generate_bai_file(file_path):
    pysam.index(file_path)


def fastq_check(file_path, number_of_reads, read_length):
    error = {}
    temp_file = tempfile.NamedTemporaryFile()
    shutil.copyfile(file_path, temp_file.name)
    fq = pyfastx.Fastq(temp_file.name)
    count = len(fq)
    avg_len = int(fq.avglen)
    logging.info(f'number of reads is {count}')
    logging.info(f'read length is {avg_len}')
    if count != number_of_reads:
        error['fastq_number_of_reads'] = f'sumbitted number of reads {number_of_reads} does not match number of reads {count} in cloud storage'
    if avg_len != read_length:
        error['fastq_read_length'] = f'sumbitted read length {read_length} does not match read length {avg_len} in cloud storage'
    fxi_file_path = temp_file.name + '.fxi'
    if os.path.exists(fxi_file_path):
        os.remove(fxi_file_path)
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


# Start script
if __name__ == '__main__':
    main()
