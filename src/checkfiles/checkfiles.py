import json
#import requests
import hashlib
import gzip
#import pysam
import json
import os
import sys
import time
from google.cloud import storage

# Retrieve User-defined env vars
MD5SUM = os.getenv('MD5SUM')
FILE_FORMAT = os.getenv('FILE_FORMAT')
UUID = os.getenv('UUID', '462bd56-9278-48aa-bc55-9eff587ba2c7')
BUCKET_NAME = os.getenv('BUCKET_NAME', 'igvf-file-validation_test_files')
BLOB_NAME = os.getenv('BLOB_NAME', 'ENCFF080HPN.tsv')

ZIP_FILE_FORMAT = [
    'bam',
    'fastq',
    'txt',
    'tsv',
]

EXCLUDE_FORMAT = [
    'bai',
]

CHECKS = {
    'BAM_QUICKCHECK': 'bam_quickcheck',
    'VALIDATE_FILES': 'validateFiles',
    'MD5SUM': 'md5sum',
    'CONTENT_MD5SUM': 'content_md5sum',
    'FILE_SIZE': 'file_size',
    'READ_COUNT': 'read_count',
    'FASTQ_SIGNATURE': 'fastq_signature',
    'BAM_STATS': 'bam_stats',
    'BAM_MAPPED_RUN_TYPE': 'bam_mapped_run_type',
    'BAM_MAPPED_READ_LENGTH': 'bam_mapped_read_length',
    'BAM_MAPPED_RUN_TYPE_EXTRACION': 'bam_mapped_run_type_extraction',
    'BAM_MAPPED_READ_LENGTH_EXTRACTION': 'bam_mapped_read_length_extraction',

}

ERRORS = {
    'ASSEMBLY': 'assembly',
    'GENOME_ANNOTATION': 'genome_annotation',
    'MD5SUM': 'md5sum',
    'CONTENT_MD5SUM': 'content_md5sum',
    'LOOKUP_FOR_CONTENT_MD5SUM': 'lookup_for_content_md5sum',
    'GZIP': 'gzip',
    'VALIDATE_FILES': 'validateFiles',
    'FASTQ_FORMAT_READ_NAME': 'fastq_format_read_name',
    'FASTQ_READ_NAME_ENCODING': 'fastq_read_name_encoding',
    'UNZIPPED_FASTQ_STREAMING': 'unzipped_fastq_streaming',
    'FASTQ_INCONSISTENT_READ_NUMBERS': 'inconsistent_read_numbers',
    'FASTQ_READ_LENGTH': 'fastq_read_lenghth',
    'FASTQ_INFORMATION_EXTRACTION': 'fastq_information_extraction',
    'FASTQ_NOT_UNIQUE_FLOWCELL_DETAILS': 'fastq_not_unique_flowcell_details',
    'BAM_STATS_DECODING_FAILURE': 'bam_stats_decoding_failure',
    'BAM_QUICKCHECK': 'bam_quickcheck',
    'BAM_STATS_EXTRACTION': 'bam_stats_extraction',
    'BAM_MISSING_MAPPED_PROPERTIES': 'bam_missing_mapped_properties',

}

# metadata for all file: derived_from
# metadata for fastq need to have: read_name_details, platform, fastq_signature


def main(bucket_name, blob_name, uuid, md5sum, file_format):
    print(f'Checking file uuid {uuid}...')
    storage_client = storage.Client(project='igvf-file-validation')
    bucket = storage_client.bucket(bucket_name)
    blob = bucket.blob(blob_name)

    errors = {}
    results = {}
    content_error = []

    is_gzipped = is_file_gzipped(blob)
    check_valid_gzipped_file_format(errors, is_gzipped, file_format)

    print(f'Completed file validation for file uuid {uuid}.')

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
        errors[ERRORS.GZIP] = 'file should be gzipped'
    if file_format not in ZIP_FILE_FORMAT and is_gzipped:
        errors[ERRORS.GZIP] = 'file should not be gzipped'
    return ''


# Start script
if __name__ == '__main__':
    try:
        response = main(BUCKET_NAME, BLOB_NAME, UUID, MD5SUM, FILE_FORMAT)
        print(json.dumps(response))
    except Exception as err:
        message = f'file uuid #{UUID} failed: {str(err)}'

        print(json.dumps({'message': message, 'severity': 'ERROR'}))
        sys.exit(1)  # Retry Job Task by exiting the process
