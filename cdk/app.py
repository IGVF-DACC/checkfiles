import json

from aws_cdk import App
from aws_cdk import Environment

from checkfiles_runner.stacks.runner import RunCheckfilesStepFunction
from checkfiles_runner.stacks.runner import RunCheckfilesStepFunctionSandbox
from checkfiles_runner.stacks.runner import RunCheckfilesStepFunctionProduction
from checkfiles_runner.config import config


ENVIRONMENT_SANDBOX = Environment(
    account=config['account_staging'],
    region=config['region']
)

ENVIRONMENT_PRODUCTION = Environment(
    account=config['account_production'],
    region=config['region']
)


AMI_ID_SANDBOX = config['ami_id_sandbox']

AMI_ID_PRODUCTION = config['ami_id_production']


INSTANCE_TYPE_SANDBOX = config['instance_type_sandbox']

INSTANCE_TYPE_PRODUCTION = config['instance_type_production']


INSTANCE_NAME_SANDBOX = config['instance_name_sandbox']

INSTANCE_NAME_PRODUCTION = config['instance_name_production']


INSTANCE_SECURITY_GROUP_SANDBOX = config['instance_security_group_sandbox']

INSTANCE_SECURITY_GROUP_PRODUCTION = config['instance_security_group_production']


INSTANCE_PROFILE_ARN_SANDBOX = config['instance_profile_arn_sandbox']

INSTANCE_PROFILE_ARN_PRODUCTION = config['instance_profile_arn_production']


CHECKFILES_BRANCH_SANDBOX = config['checkfiles_branch_sandbox']

CHECKFILES_BRANCH_PRODUCTION = config['checkfiles_branch_production']


PORTAL_SECRETS_ARN_SANDBOX = config['portal_secrets_arn_sandbox']

PORTAL_SECRETS_ARN_PRODUCTION = config['portal_secrets_arn_production']


BACKEND_URI_SANDBOX = config['backend_uri_sandbox']

BACKEND_URI_PRODUCTION = config['backend_uri_production']

app = App()


RunCheckfilesStepFunctionSandbox(
    app,
    'RunCheckfilesStepFunctionSandbox',
    ami_id=AMI_ID_SANDBOX,
    instance_type=INSTANCE_TYPE_SANDBOX,
    instance_name=INSTANCE_NAME_SANDBOX,
    instance_profile_arn=INSTANCE_PROFILE_ARN_SANDBOX,
    instance_security_group=INSTANCE_SECURITY_GROUP_SANDBOX,
    checkfiles_branch=CHECKFILES_BRANCH_SANDBOX,
    portal_secrets_arn=PORTAL_SECRETS_ARN_SANDBOX,
    backend_uri=BACKEND_URI_SANDBOX,
    env=ENVIRONMENT_SANDBOX,
)


RunCheckfilesStepFunctionProduction(
    app,
    'RunCheckfilesStepFunctionProduction',
    ami_id=AMI_ID_PRODUCTION,
    instance_type=INSTANCE_TYPE_PRODUCTION,
    instance_name=INSTANCE_NAME_PRODUCTION,
    instance_profile_arn=INSTANCE_PROFILE_ARN_PRODUCTION,
    instance_security_group=INSTANCE_SECURITY_GROUP_PRODUCTION,
    checkfiles_branch=CHECKFILES_BRANCH_PRODUCTION,
    portal_secrets_arn=PORTAL_SECRETS_ARN_PRODUCTION,
    backend_uri=BACKEND_URI_PRODUCTION,
    env=ENVIRONMENT_PRODUCTION,
)
app.synth()
