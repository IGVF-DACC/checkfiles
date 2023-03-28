import boto3
import gzip
import json
import logging
import os

from io import BufferedReader

import requests


logging.basicConfig(
    level=logging.INFO,
    force=True
)


FILE_FORMAT_TO_VALIDATOR = {
    'fastq': is_fastq_gz
}

def is_fastq_gz(url):
    def valid_line_structure(line, line_number):
        if line_number % 4 == 1:
            return line.startswith(b'@')
        elif line_number % 4 == 3:
            return line.startswith(b'+')
        else:
            return all(x in b'ATCGNatcgn' for x in line.rstrip())

    response = requests.get(url, stream=True)
    if response.status_code != 200:
        return False

    try:
        with gzip.open(BufferedReader(response.raw)) as gz:
            line_number = 0
            for line in gz:
                if not valid_line_structure(line, line_number):
                    return False
                line_number += 1
            return line_number % 4 == 0
    except Exception as e:
        print(f"An error occurred while processing the file: {e}")
        return False

def validate_file(file_format, url):
    try:
        return {
            'file_format': file_format,
            'is_valid': FILE_FORMAT_TO_VALIDATOR[file_format](url)
        }
    except KeyError:
        return {
            'file_format': file_format,
            'is_valid': 'unknown file format'
        }

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

def get_file_format_from_message(message: dict) -> str:
    body = json.loads(message['Body'])
    file_format = body['file_format']
    return file_format


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
        file_format = get_file_format_from_message(message)
        logging.info(f'Validating {file_format} file in {presigned_download_url}')
        validation_result = validate_file(file_format, presigned_download_url)
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

