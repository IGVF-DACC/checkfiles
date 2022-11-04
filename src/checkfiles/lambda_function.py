import json
import requests
import boto3
import hashlib
import os
import gzip


def lambda_handler(event, context):
    sqs_records = event['Records']
    files = []
    for sqs in sqs_records:
        sqs_body_json = json.loads(sqs['body'])
        file_records = sqs_body_json['Records']
        for file in file_records:
            key = file['s3']['object']['key']
            if key[-1] != '/':
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
            md5sum_encode = file_metadata['md5sum']
            file_size_encode = file_metadata['file_size']
            errors = {}
            if md5sum_encode != file['etag']:
                calculated_md5sum = calculate_md5sum(
                    file['bucket'], file['key'])
                if calculated_md5sum != md5sum_encode:
                    errors['md5sum'] = 'File metadata-specified md5sum ' + md5sum_encode + \
                        ' does not match the calculated md5sum ' + calculated_md5sum
            if file['file_size_s3'] != file_size_encode:
                errors['file_size'] = 'Encode metadata specified file size ' + str(file_size_encode) + \
                    ' does not match the size of the file in S3 bucket ' + \
                    str(file['file_size_s3'])
            if is_qz_file(file['key']):
                content_md5sum = calculate_content_md5sum(
                    file['bucket'], file['key'])
                print('content_md5sum:', content_md5sum)
            if errors:
                return_data.append({
                    'accession': accession,
                    'status': 'content error',
                    'errors': errors
                })
            else:
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


def is_qz_file(key):
    return key.split('.')[-1] == 'gz'
