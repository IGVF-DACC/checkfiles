import json
#import requests
import hashlib
import gzip
#import pysam
import json
import os
import sys
import time
import logging
from google.cloud import storage

# Retrieve User-defined env vars
BUCKET_NAME = os.getenv('BUCKET_NAME', 'igvf-file-validation_test_files')
BLOB_NAME = os.getenv('BLOB_NAME', 'ENCFF080HPN.tsv')
MD5SUM = os.getenv('MD5SUM')
FILE_FORMAT = os.getenv('FILE_FORMAT', 'tsv')
UUID = os.getenv('UUID', '462bd56-9278-48aa-bc55-9eff587ba2c7')
FILE_SIZE = os.getenv('FILE_SIZE', 1439779)

ZIP_FILE_FORMAT = [
    'bam',
    'fastq',
    'txt',
    'tsv',
]

EXCLUDE_FORMAT = [
    'bai',
]

'''
Items to check:
bam_quickcheck
validateFiles
md5sum
content_md5sum
file_size
read_count
fastq_signature
bam_stats
bam_mapped_run_type
bam_mapped_read_length
bam_mapped_run_type_extraction
bam_mapped_read_length_extraction


All the errors are listed here:
assembly
genome_annotation
md5sum
content_md5sum
lookup_for_content_md5sum
gzip
file_size
validateFiles
fastq_format_read_name
fastq_read_name_encoding
unzipped_fastq_streaming
inconsistent_read_numbers
fastq_read_lenghth
fastq_information_extraction
fastq_not_unique_flowcell_details
bam_stats_decoding_failure
bam_quickcheck
bam_stats_extraction
bam_missing_mapped_properties
'''


# metadata for all file: derived_from
# metadata for fastq need to have: read_name_details, platform, fastq_signature
logging.basicConfig(
    format='%(asctime)s | %(levelname)s: %(message)s', level=logging.NOTSET)


def main(bucket_name, blob_name, uuid, md5sum, file_format, file_size):
    logging.info(f'Checking file uuid {uuid}...')
    storage_client = storage.Client(project='igvf-file-validation')
    bucket = storage_client.bucket(bucket_name)
    blob = bucket.get_blob(blob_name)

    errors = {}
    results = {}
    content_error = []

    is_gzipped = is_file_gzipped(blob)
    logging.info(f'is file gziped: {is_gzipped}')
    check_valid_gzipped_file_format(errors, is_gzipped, file_format)
    results['file_size'] = blob.size
    check_file_size(errors, file_size, blob.size)

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


def update_content_error(errors, error_message):
    if 'content_error' not in errors:
        errors['content_error'] = error_message
    else:
        errors['content_error'] += ', ' + error_message


def is_file_gzipped(blob):
    with blob.open('rb') as f:
        try:
            gzip.GzipFile(fileobj=f).read(1)
            return True
        except gzip.BadGzipFile:
            return False


def check_valid_gzipped_file_format(errors, is_gzipped, file_format):
    if file_format in ZIP_FILE_FORMAT and not is_gzipped:
        errors['gzip'] = f'{file_format} file should be gzipped'
    elif file_format not in ZIP_FILE_FORMAT and is_gzipped:
        errors['gzip'] = f'{file_format} file should not be gzipped'


def check_file_size(errors, file_size, blob_size):
    if blob_size != file_size:
        errors['file_size'] = f'submitted file zise {str(file_size)} does not mactch file zise {str(blob_size)}'


# Start script
if __name__ == '__main__':
    try:
        response = main(BUCKET_NAME, BLOB_NAME, UUID,
                        MD5SUM, FILE_FORMAT, FILE_SIZE)
        logging.info(json.dumps(response))
    except Exception as err:
        message = f'file uuid #{UUID} failed: {str(err)}'

        logging.info(json.dumps({'message': message, 'severity': 'ERROR'}))
        sys.exit(1)  # Retry Job Task by exiting the process
