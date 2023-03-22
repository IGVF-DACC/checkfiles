import boto3
import json
import logging
import os


logging.basicConfig(
    level=logging.INFO,
    force=True
)


def get_queue_url():
    return os.environ['PENDING_FILES_QUEUE_URL']

def get_sqs_client():
    return boto3.client('sqs')

def get_message_from_queue(queue_url):
    client = get_sqs_client()
    response = client.receive_message(
            QueueUrl=queue_url
    )
    if not response:
        logging.info(f'No messages in queue')
        return None
    number_of_messages = len(response.get('Messages'))
    logging.info(f'Got {number_of_messages} messages')
    return response

def try_to_handle_message(queue_url):
    response = get_message_from_queue(queue_url)
    if not response:
        logging.info('No messages in queue')
    else:
        messages = response['Messages']
        message = messages[0]
        receipt_handle = message['ReceiptHandle']
        logging.info(f'Received message with ReceiptHandle: {receipt_handle}')
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

