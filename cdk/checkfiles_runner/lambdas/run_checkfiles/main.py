import json
import os


import boto3


def get_secret_arn():
    return os.environ['PORTAL_SECRETS_ARN']


def get_backend_uri():
    return os.environ['BACKEND_URI']


def get_portal_key(secret):
    return secret['PORTAL_KEY']


def get_portal_secret_key(secret):
    return secret['PORTAL_SECRET_KEY']


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
    return json.loads(secret)


def run_checkfiles_command(event, context):
    instance_id = event['instance_id']
    backend_uri = get_backend_uri()
    secret_arn = get_secret_arn()
    secret = get_secret(secret_arn)
    portal_key = get_portal_key(secret)
    portal_secret_key = get_portal_secret_key(secret)
    command = f'venv/bin/python src/checkfiles/checkfiles.py --server {backend_uri} --portal-key-id {portal_key} --portal-secret-key {portal_secret_key} --patch'
    ssm = boto3.client('ssm')
    response = ssm.send_command(
        InstanceIds=[instance_id],
        DocumentName='AWS-RunShellScript',
        Parameters={'commands': [
            command
        ],
            'workingDirectory': ['/home/ubuntu/checkfiles'],
        },
        CloudWatchOutputConfig={
            'CloudWatchLogGroupName': 'checkfiles-test-log',
            'CloudWatchOutputEnabled': True,
        }
    )

    return {'instance_id': instance_id, 'command_id': response['Command']['CommandId']}
