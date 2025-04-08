import json

from aws_cdk import App
from aws_cdk import Environment

from checkfiles_runner.stacks.runner import RunCheckfilesStepFunctionProps
from checkfiles_runner.stacks.runner import RunCheckfilesStepFunction
from checkfiles_runner.stacks.runner import RunCheckfilesStepFunctionSandbox
from checkfiles_runner.stacks.runner import RunCheckfilesStepFunctionProduction
from checkfiles_runner.config import config


ENVIRONMENT_PRODUCTION = Environment(
    account=config['account_production'],
    region=config['region']
)

production_props = RunCheckfilesStepFunctionProps(
    ami_id=config['ami_id_production'],
    instance_name=config['instance_name_production'],
    instance_profile_arn=config['instance_profile_arn_production'],
    instance_security_group_id=config['instance_security_group_production'],
    checkfiles_tag=config['checkfiles_tag_production'],
    portal_secrets_arn=config['portal_secrets_arn_production'],
    backend_uri=config['backend_uri_production'],
)


app = App()

RunCheckfilesStepFunctionProduction(
    app,
    'RunCheckfilesStepFunctionProduction',
    props=production_props,
    env=ENVIRONMENT_PRODUCTION,
)
app.synth()
