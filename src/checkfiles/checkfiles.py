import json
import requests
import hashlib
import gzip
import pysam
import pyfastx
import json
import os
import sys
import time
import logging
import base64
import binascii
from google.cloud import storage

# some files for test: ENCFF594AYI.fastq.gz, ENCFF206HGF.bam, ENCFF080HPN.tsv
BUCKET_NAME = os.getenv('BUCKET_NAME', 'igvf-file-validation_test_files')
BLOB_NAME = os.getenv('BLOB_NAME', 'ENCFF594AYI.fastq.gz')
MD5SUM = os.getenv('MD5SUM', '3e814f4af7a4c13460584b26fbe32dc4')
FILE_FORMAT = os.getenv('FILE_FORMAT', 'fastq')
UUID = os.getenv('UUID', '462bd56-9278-48aa-bc55-9eff587ba2c7')
FILE_SIZE = os.getenv('FILE_SIZE', 1371)
NUMBER_OF_READS = os.getenv('NUMBER_OF_READS', 25)
READ_LENGTH = os.getenv('READ_LENGTH', 58)

ZIP_FILE_FORMAT = [
    'bam',
    'fastq',
    'txt',
    'tsv',
]

EXCLUDE_FORMAT = [
    'bai',
]

CONTENT_MD5SUM_URL = 'https://www.encodeproject.org/search/?type=File&format=json&content_md5sum='


# metadata for all file: derived_from
# metadata for fastq need to have: read_name_details, platform, fastq_signature
logging.basicConfig(
    format='%(asctime)s | %(levelname)s: %(message)s', level=logging.INFO)


def main():
    try:
        response = file_validation(BUCKET_NAME, BLOB_NAME, UUID,
                                   MD5SUM, FILE_FORMAT, FILE_SIZE, NUMBER_OF_READS, READ_LENGTH)
        logging.info(json.dumps(response))
    except Exception as err:
        message = f'exception occurred when checking file uuid #{UUID}: {str(err)}'

        logging.info(json.dumps({'exception': message}))
        sys.exit(1)  # Retry Job Task by exiting the process


def file_validation(bucket_name, blob_name, uuid, md5sum, file_format, file_size, number_of_reads, read_length):
    logging.info(f'Checking file uuid {uuid}...')
    storage_client = storage.Client(project='igvf-file-validation')
    bucket = storage_client.bucket(bucket_name)
    blob = bucket.get_blob(blob_name)
    file_path = get_local_file_path(blob_name)

    errors = {}
    results = {}

    is_gzipped = is_file_gzipped(file_path)
    logging.info(f'is file gziped: {is_gzipped}')
    check_valid_gzipped_file_format(errors, is_gzipped, file_format)
    results['file_size'] = blob.size
    check_file_size(errors, file_size, blob.size)
    check_md5sum(errors, md5sum, blob.md5_hash)

    if is_gzipped:
        check_content_md5sum(errors, file_path)

    if file_format == 'bam':
        bam_pysam_check(errors, file_path, number_of_reads)
        if 'bam_error' not in errors:
            bam_generate_bai_file(file_path)
    elif file_format == 'fastq':
        fastq_check(errors, file_path, number_of_reads, read_length)

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


def get_local_file_path(blob_name):
    file_path = '/mnt/' + blob_name
    return file_path


def is_file_gzipped(file_path):
    try:
        gzip.GzipFile(filename=file_path).read(1)
        return True
    except gzip.BadGzipFile:
        return False


def check_valid_gzipped_file_format(errors, is_gzipped, file_format):
    if file_format in ZIP_FILE_FORMAT and not is_gzipped:
        errors['gzip'] = f'{file_format} file should be gzipped'
    elif file_format not in ZIP_FILE_FORMAT and is_gzipped:
        errors['gzip'] = f'{file_format} file should not be gzipped'


def check_file_size(errors, file_size, size_in_cloud_storage):
    if size_in_cloud_storage != file_size:
        errors['file_size'] = f'submitted file zise {str(file_size)} does not mactch file zise {str(size_in_cloud_storage)} in cloud storage'


def check_md5sum(errors, md5sum, md5_base64):
    blob_md5sum = str(binascii.hexlify(
        base64.urlsafe_b64decode(md5_base64)), 'utf-8')
    logging.info(f'the md5sum is {blob_md5sum}')
    if md5sum != blob_md5sum:
        errors['md5sum'] = f'submitted file md5sum {(md5sum)} does not mactch file md5sum {blob_md5sum} in cloud storage'


def check_content_md5sum(errors, file_path, chunk_size=128*6400000):
    md5 = hashlib.md5()
    with gzip.open(file_path) as f:
        while chunk := f.read(chunk_size):
            md5.update(chunk)
    content_md5sum = md5.hexdigest()
    logging.info(f'content md5sum is {content_md5sum}')
    url = CONTENT_MD5SUM_URL + content_md5sum
    session = requests.Session()
    username = os.getenv('ENCODE_ACCESS_KEY')
    password = os.getenv('ENCODE_CECRET_KEY')
    session.auth = (username, password)
    conflict_files = session.get(url).json()['@graph']
    if conflict_files:
        accessions = []
        for file in conflict_files:
            accessions.append(file['accession'])
        errors[
            'content_md5sum'] = f"content md5sum conflicts with content md5sum of existing file(s): {', '.join(accessions)}"


def bam_pysam_check(errors, file_path, number_of_reads):
    try:
        pysam.quickcheck(file_path)
        result = pysam.stats(file_path)
        if 'SN\tis sorted:\t0' in result:
            errors['bam_error'] = 'the bam file is not sorted'
        else:
            samfile = pysam.AlignmentFile(file_path, 'rb')
            count = samfile.count(until_eof=True)
            logging.info(f'the number of reads: {count}')
            if count != number_of_reads:
                errors['bam_error'] = f'sumbitted number of reads {number_of_reads} does not match number of reads {count} in cloud storage'
            samfile.close()
    except pysam.utils.SamtoolsError as e:
        errors['bam_error'] = f'file is not valid bam file by SamtoolsError: {str(e)}'


def bam_generate_bai_file(file_path):
    pysam.index(file_path)


def fastq_check(errors, file_path, number_of_reads, read_length):
    fq = pyfastx.Fastq(file_path)
    count = len(fq)
    avg_len = int(fq.avglen)
    if count != number_of_reads:
        errors['fastq_number_of_reads'] = f'sumbitted number of reads {number_of_reads} does not match number of reads {count} in cloud storage'
    if avg_len != read_length:
        errors['fastq_read_length'] = f'sumbitted read length {read_length} does not match read length {avg_len} in cloud storage'
    fxi_file_path = file_path + '.fxi'
    if os.path.exists(fxi_file_path):
        os.remove(fxi_file_path)


# Start script
if __name__ == '__main__':
    main()
