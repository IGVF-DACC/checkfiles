import json

from aws_cdk import App
from aws_cdk import Environment

from checkfiles_runner.stacks.runner import RunCheckfilesStepFunctionProps
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

sandbox_props = RunCheckfilesStepFunctionProps(
    ami_id=config['ami_id_sandbox'],
    instance_name=config['instance_name_sandbox'],
    instance_profile_arn=config['instance_profile_arn_sandbox'],
    instance_security_group_id=config['instance_security_group_sandbox'],
    checkfiles_tag=config['checkfiles_branch_sandbox'],
    portal_secrets_arn=config['portal_secrets_arn_sandbox'],
    backend_uri=config['backend_uri_sandbox'],
)


production_props = RunCheckfilesStepFunctionProps(
    ami_id=config['ami_id_production'],
    instance_name=config['instance_name_production'],
    instance_profile_arn=config['instance_profile_arn_production'],
    instance_security_group_id=config['instance_security_group_production'],
    checkfiles_tag=config['checkfiles_branch_production'],
    portal_secrets_arn=config['portal_secrets_arn_production'],
    backend_uri=config['backend_uri_production'],
)


app = App()


RunCheckfilesStepFunctionSandbox(
    app,
    'RunCheckfilesStepFunctionSandbox',
    props=sandbox_props,
    env=ENVIRONMENT_SANDBOX,
)


RunCheckfilesStepFunctionProduction(
    app,
    'RunCheckfilesStepFunctionProduction',
    props=production_props,
    env=ENVIRONMENT_PRODUCTION,
)
app.synth()
