import boto3
import json
import os
import requests

import logging
from botocore.exceptions import ClientError

logging.basicConfig(
    level=logging.INFO,
    force=True
)

PENDING_FILES_SEARCH = '/search?type=File&upload_status=pending&field=href&field=uuid&field=upload_status&field=file_format&field=content_md5sum&field=md5sum'

def get_portal_key(secret):
    return secret['IGVF_PORTAL_KEY']

def get_portal_secret_key(secret):
    return secret['IGVF_PORTAL_SECRET_KEY']

def get_auth(secret):
    return (get_portal_key(secret), get_portal_secret_key(secret))

def get_sqs_queue():
    return os.environ['SQS_QUEUE_URL']

def get_portal_url():
    return os.environ['PORTAL_URL']

def get_secrets_arn():
    return os.environ['PORTAL_SECRETS_ARN']

def get_sqs_client():
    return boto3.client('sqs')

def send_message(client,queue_url, message_body):
    response = client.send_message(
        QueueUrl=queue_url,
        MessageBody=message_body
    )
    return response

def get_secret(secret_arn):
    session = boto3.session.Session()
    client = session.client(
        service_name='secretsmanager'
    )
    try:
        get_secret_value_response = client.get_secret_value(
            SecretId=secret_arn
        )
    except ClientError as e:
        raise e
    secret = get_secret_value_response['SecretString']
    logging.info(f'got secret from {secret_arn}')
    return json.loads(secret)

def get_pending_files(secret, portal_url):
    headers = {'accept': 'application/json'}
    auth = get_auth(secret)
    response = requests.get(
        portal_url + PENDING_FILES_SEARCH,
        headers=headers,
        auth=auth,
    )
    pending_files = response.json()['@graph']
    return pending_files


def put_pending_files(event, context):
    sqs_client = get_sqs_client()
    queue_url = get_sqs_queue()
    secret_arn = get_secrets_arn()
    secret = get_secret(secret_arn)
    portal_url = get_portal_url()
    pending_files = get_pending_files(secret, portal_url)
    number_of_pending = len(pending_files)
    logging.info(f'putting {number_of_pending} messages to: {queue_url}')
    for fileobj in pending_files:
        msg = json.dumps(fileobj)
        send_message(sqs_client,queue_url, msg)
