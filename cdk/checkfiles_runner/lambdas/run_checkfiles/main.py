import json
import os


import boto3


TWENTY_THREE__HOURS_IN_SECONDS = str(23 * 3600)


def get_secret_arn():
    return os.environ['PORTAL_SECRETS_ARN']


def get_backend_uri():
    return os.environ['BACKEND_URI']


def run_checkfiles_command(event, context):
    instance_id = event['instance_id']
    backend_uri = get_backend_uri()
    secret_arn = get_secret_arn()
    put_portal_key_to_env_cmd = f"export PORTAL_KEY=$(aws secretsmanager get-secret-value --region us-west-2 --secret-id {secret_arn} --output text | awk '{{print $4}}' | jq -r .PORTAL_KEY)"
    put_secret_key_to_env_cmd = f"export PORTAL_SECRET_KEY=$(aws secretsmanager get-secret-value --region us-west-2 --secret-id {secret_arn} --output text | awk '{{print $4}}' | jq -r .PORTAL_SECRET_KEY)"
    put_home_to_env_cmd = 'export HOME=/home/ubuntu'
    run_checkfiles_cmd = f'venv/bin/python src/checkfiles/checkfiles.py --server {backend_uri} --portal-key-id $(echo $PORTAL_KEY) --portal-secret-key $(echo $PORTAL_SECRET_KEY) --patch'
    ssm = boto3.client('ssm')
    response = ssm.send_command(
        InstanceIds=[instance_id],
        DocumentName='AWS-RunShellScript',
        Parameters={'commands': [
            put_portal_key_to_env_cmd,
            put_secret_key_to_env_cmd,
            put_home_to_env_cmd,
            run_checkfiles_cmd,
        ],
            'workingDirectory': ['/home/ubuntu/checkfiles'],
            'executionTimeout': [TWENTY_THREE__HOURS_IN_SECONDS],
        },
        CloudWatchOutputConfig={
            'CloudWatchLogGroupName': 'checkfiles-log',
            'CloudWatchOutputEnabled': True,
        }
    )
    iterator = event['iterator']

    return {'instance_id': instance_id,
            'command_id': response['Command']['CommandId'],
            'iterator': iterator
            }
