import boto3
import json
import logging
import os

import requests


logging.basicConfig(
    level=logging.INFO,
    force=True
)

def get_portal_key():
    return os.environ['IGVF_PORTAL_KEY']

def get_portal_secret_key():
    return os.environ['IGVF_PORTAL_SECRET_KEY']

def get_portal_auth():
    return (get_portal_key(), get_portal_secret_key())

def get_queue_url():
    return os.environ['PENDING_FILES_QUEUE_URL']

def get_portal_url():
    return os.environ['PORTAL_URL']

def get_sqs_client():
    return boto3.client('sqs')

def get_message_from_queue(queue_url):
    client = get_sqs_client()
    response = client.receive_message(
            QueueUrl=queue_url
    )
    if 'Messages' not in response:
        logging.info(f'No messages in queue')
        return None
    number_of_messages = len(response.get('Messages'))
    logging.info(f'Got {number_of_messages} messages')
    return response

def build_redirect_url_from_message(message: dict) -> str:
    body = json.loads(message['Body'])
    href = body['href']
    soft_redirect_url = get_portal_url() + href + '?soft=true'
    return soft_redirect_url


def try_to_handle_message(queue_url):
    response = get_message_from_queue(queue_url)
    if not response:
        logging.info('No messages in queue')
    else:
        messages = response['Messages']
        message = messages[0]
        redirect_url = build_redirect_url_from_message(message)
        receipt_handle = message['ReceiptHandle']
        logging.info(f'Received message with ReceiptHandle: {receipt_handle}')
        logging.info(f'Got redirect url: {redirect_url}, will get presigned url.')
        redirect_response = requests.get(redirect_url, auth=get_portal_auth())
        presigned_download_url = redirect_response.json()['location']
        logging.info(f'Got presigned download url: {presigned_download_url}')
        client = get_sqs_client()
        logging.info(f'Deleting message')
        client.delete_message(
            QueueUrl=queue_url,
            ReceiptHandle=receipt_handle
        )
        logging.info(f'ReceiptHandle {receipt_handle} handled and deleted')
    return response


def main():
    logging.info('In main')
    queue_url = get_queue_url()
    logging.info(f'Trying to handle a message')
    response = try_to_handle_message(queue_url)


if __name__ == "__main__":
    main()

