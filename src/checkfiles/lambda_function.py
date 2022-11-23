import json
import requests
import boto3
import hashlib
import os
import gzip
import pysam

ZIP_FILE_FORMAT = [
    'bam',
    'fastq',
    'txt',
    'tsv',
]

EXCLUDE_FORMAT = [
    'bai',
]


def lambda_handler(event, context):
    sqs_records = event['Records']
    files = []
    for sqs in sqs_records:
        sqs_body_json = json.loads(sqs['body'])
        file_records = sqs_body_json['Records']
        for file in file_records:
            key = file['s3']['object']['key']
            if key[-1] or key.split('.')[-1] not in EXCLUDE_FORMAT:
                file = {
                    'bucket': file['s3']['bucket']['name'],
                    'key': key,
                    'file_size_s3': file['s3']['object']['size'],
                    'etag': file['s3']['object']['eTag'],
                    'accession': key.split('/')[-1].split('.')[0]
                }
                files.append(file)

    if not files:
        return None
    return_data = []
    for file in files:
        accession = file['accession']
        file_metadata = get_file_metadata_from_encode(accession)
        if not file_metadata or file_metadata.get('accession') == None:
            raise Exception('accession', accession, 'is not found')
        if file_metadata['status'] == 'uploading':
            error = general_file_check(file, file_metadata)

            if error:
                return_data.append({
                    'accession': accession,
                    'status': 'content error',
                    'error': error
                })
                continue

            error = check_bam_file(file)

            if error:
                return_data.append({
                    'accession': accession,
                    'status': 'content error',
                    'error': error
                })
                continue

            return_data.append({
                'accession': accession,
                'status': 'progress'
            })
    return return_data


def get_file_metadata_from_encode(accession):
    file_metadata = None
    session = requests.Session()
    username = os.environ.get('USERNAME')
    password = os.environ.get('PASSWORD')
    session.auth = (username, password)
    url = 'https://www.encodeproject.org/files/' + accession + '?format=json'
    response = session.get(url)
    if response.status_code == 200:
        file_metadata = response.json()
    return file_metadata


def general_file_check(file, file_metadata):
    if file['file_size_s3'] != file_metadata['file_size']:
        return 'Encode metadata specified file size ' + str(file_metadata['file_size']) + \
            ' does not match the size of the file in S3 bucket ' + \
            str(file['file_size_s3'])
    is_gzipped = is_file_gzipped(file['key'])
    error = check_valid_gzipped_file_format(
        is_gzipped, file_metadata['file_format'])
    if error:
        return error
    error = check_md5sum(file_metadata['md5sum']. file)
    if error:
        return error
    if is_gzipped:
        error = check_content_md5sum()
        if error:
            return error
    return ''


def check_md5sum(md5sum_encode, file):

    if md5sum_encode != file['etag']:
        calculated_md5sum = calculate_md5sum(
            file['bucket'], file['key'])
        if calculated_md5sum != md5sum_encode:
            return 'File metadata-specified md5sum ' + md5sum_encode + \
                ' does not match the calculated md5sum ' + calculated_md5sum
    return ''


def check_content_md5sum(file):
    content_md5sum = calculate_content_md5sum(
        file['bucket'], file['key'])
    print('content_md5sum:', content_md5sum)
    url = 'https://www.encodeproject.org/search/?type=File&format=json&content_md5sum=' + content_md5sum
    num = len(requests.get(url).json()['@graph'])
    if num > 0:
        return 'duplicated content md5sum: ' + content_md5sum
    return ''


def calculate_md5sum(bucket, key, chunk_size=128*6400):
    s3 = boto3.client('s3')
    response = s3.get_object(Bucket=bucket, Key=key)
    md5 = hashlib.md5()
    for chunk in response['Body'].iter_chunks(chunk_size=chunk_size):
        md5.update(chunk)
    return md5.hexdigest()


def calculate_content_md5sum(bucket, key, chunk_size=128*6400000):
    s3 = boto3.client('s3')
    response = s3.get_object(Bucket=bucket, Key=key)
    md5 = hashlib.md5()
    with gzip.open(response['Body']) as f:
        while chunk := f.read(chunk_size):
            md5.update(chunk)
    return md5.hexdigest()


def is_file_gzipped(bucket, key):
    s3 = boto3.client('s3')
    response = s3.get_object(Bucket=bucket, Key=key)
    with gzip.open(response['Body']) as f:
        magic_number = f.read(2)
    return magic_number == b'\x1f\x8b'


def check_valid_gzipped_file_format(is_gzipped, file_format):
    if file_format in ZIP_FILE_FORMAT and not is_gzipped:
        return 'file should be gzipped'
    if file_format not in ZIP_FILE_FORMAT and is_gzipped:
        return 'file should not be gzipped'
    return ''


def check_bam_file(file):
    s3 = boto3.client('s3')
    response = s3.get_object(Bucket=file['bucket'], Key=file['key'])
    try:
        pysam.quickcheck(response['Body'])
    except pysam.utils.SamtoolsError as e:
        return {
            'bam_quickcheck_error': str(e)
        }
    result = pysam.stats(response['Body'])
    if 'SN\tis sorted:\t0' in result:
        return {
            'bam_sort_error': 'the bam file is not sorted'
        }
    else:
        return ''


def get_number_of_reads_bam(filename):
    samfile = pysam.AlignmentFile(filename, 'rb')
    count = samfile.count()
    samfile.close()
    return count


def generate_bai_file(filename):
    pysam.index(filename)
