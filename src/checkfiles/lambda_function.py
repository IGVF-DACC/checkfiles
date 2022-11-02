import json
import requests
import boto3
import hashlib
import os

def lambda_handler(event, context):
    bucket = event['Records'][0]['s3']['bucket']['name']
    key = event['Records'][0]['s3']['object']['key']
    file_size_s3 = event['Records'][0]['s3']['object']['size']
    etag = event['Records'][0]['s3']['object']['eTag']
    if key[-1] != '/':
        accession = key.split('/')[-1].split('.')[0]
        file_metadata = get_file_metadata_from_encode(accession)
        md5sum_encode = file_metadata['md5sum']
        file_size_encode = file_metadata['file_size']
        errors = {}
        if md5sum_encode != etag:
            calculated_md5sum = calculate_checksum(bucket, key)
            if calculated_md5sum != etag:
                errors['md5sum'] = 'File metadata-specified md5sum ' + md5sum_encode + 'does not match the calculated md5sum ' + calculated_md5sum
        if file_size_s3 != file_size_encode:
                errors['file_size'] = 'File metadata-specified file_size ' + file_size_encode + 'does not match the size of the file in S3 bucket ' + file_size_s3
        if errors:
            return {
            'accession': accession,
            'status': 'content error',
            'errors': errors
        }
        else:
            return {
            'accession': accession,
            'status': 'progress'
            }           
    return None

def get_file_metadata_from_encode(accession):
    session = requests.Session()
    username = os.environ['USERNAME']
    password = os.environ['PASSWORD']
    session.auth = (username, password)
    url = 'https://www.encodeproject.org/files/' + accession + '?format=json'
    response = session.get(url)
    file_metadata = response.json()  
    return file_metadata

def calculate_checksum(bucket, key):
    s3 = boto3.client('s3')
    response = s3.get_object(Bucket=bucket, Key=key)
    file_content = response['Body'].read()
    md5 = hashlib.md5(file_content).hexdigest()
    return md5
