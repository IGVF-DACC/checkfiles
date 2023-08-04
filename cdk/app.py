import json

from aws_cdk import App
from aws_cdk import Environment

from checkfiles_runner.stacks.runner import RunCheckfilesStepFunction
from checkfiles_runner.stacks.runner import RunCheckfilesStepFunctionSandbox
from checkfiles_runner.stacks.runner import RunCheckfilesStepFunctionProduction
from checkfiles_runner.config import config


ENVIRONMENT = Environment(
    account=config['account'],
    region=config['region']
)

AMI_ID = config['ami_id']
PORTAL_SECRETS_ARN = config['portal_secrets_arn']


INSTANCE_TYPE_SANDBOX = config['instance_type_sandbox']

INSTANCE_NAME_SANDBOX = config['instance_name_sandbox']

CHECKFILES_BRANCH_SANDBOX = config['checkfiles_branch_sandbox']

BACKEND_URI_SANDBOX = config['backend_uri_sandbox']


INSTANCE_TYPE_PRODUCTION = config['instance_type_production']

INSTANCE_NAME_PRODUCTION = config['instance_name_production']

CHECKFILES_BRANCH_PRODUCTION = config['checkfiles_branch_production']

BACKEND_URI_PRODUCTION = config['backend_uri_production']

app = App()


RunCheckfilesStepFunctionSandbox(
    app,
    'RunCheckfilesStepFunctionSandbox',
    ami_id=AMI_ID,
    instance_type=INSTANCE_TYPE_SANDBOX,
    instance_name=INSTANCE_NAME_SANDBOX,
    checkfiles_branch=CHECKFILES_BRANCH_SANDBOX,
    portal_secrets_arn=PORTAL_SECRETS_ARN,
    backend_uri=BACKEND_URI_SANDBOX,
    env=ENVIRONMENT,
)


RunCheckfilesStepFunctionProduction(
    app,
    'RunCheckfilesStepFunctionProduction',
    ami_id=AMI_ID,
    instance_type=INSTANCE_TYPE_PRODUCTION,
    instance_name=INSTANCE_NAME_PRODUCTION,
    checkfiles_branch=CHECKFILES_BRANCH_PRODUCTION,
    portal_secrets_arn=PORTAL_SECRETS_ARN,
    backend_uri=BACKEND_URI_PRODUCTION,
    env=ENVIRONMENT,
)
app.synth()
