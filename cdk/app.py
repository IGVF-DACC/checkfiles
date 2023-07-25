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

app = App()


RunCheckfilesStepFunction(
    app,
    'RunCheckfilesStepFunction',
    env=ENVIRONMENT,
)
app.synth()
