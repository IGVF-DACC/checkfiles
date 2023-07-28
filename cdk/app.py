import json

from aws_cdk import App
from aws_cdk import Environment

from checkfiles_runner.stacks.runner import RunCheckfilesStepFunction
from checkfiles_runner.config import config


ENVIRONMENT = Environment(
    account=config['account'],
    region=config['region']
)

AMI_ID = config['ami_id']

INSTANCE_TYPE = config['instance_type']

INSTANCE_NAME = config['instance_name']

PORTAL_SECRETS_ARN = config['portal_secrets_arn']

BACKEND_URI = config['backend_uri']

app = App()


RunCheckfilesStepFunction(
    app,
    'RunCheckfilesStepFunction',
    ami_id=AMI_ID,
    instance_type=INSTANCE_TYPE,
    instance_name=INSTANCE_NAME,
    portal_secrets_arn=PORTAL_SECRETS_ARN,
    backend_uri=BACKEND_URI,
    env=ENVIRONMENT,
)
app.synth()
