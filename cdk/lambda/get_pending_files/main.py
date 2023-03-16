import boto3
import os
import requests

import logging
from botocore.exceptions import ClientError

logging.basicConfig(
    level=logging.INFO,
    force=True
)

def get_portal_key():
    return os.environ['ENCODE_PORTAL_KEY']

def get_portal_secret_key():
    return os.environ['ENCODE_PORTAL_SECRET_KEY']

def get_sqs_queue():
    return os.environ['SQS_QUEUE_URL']

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
    return secret

def put_pending_files(event, context):
    sqs_client = get_sqs_client()
    queue_url = get_sqs_queue()
    secret_arn = get_secrets_arn()
    secret = get_secret(secret_arn)
    logging.info(f'putting message to: {queue_url}')
    send_message(sqs_client,queue_url,'Hello from lambda, queue!')
