import pytest
import json

from aws_cdk import App
from aws_cdk import Environment

from aws_cdk.assertions import Template


PORTAL_SECRETS_ARN = 'arn:aws:secretsmanager:us-west-2:123456:secret:testing-secret-123456'

INSTANCE_PROFILE_ARN = 'arn:aws:iam::123456:instance-profile/checkfiles-instance'


ENVIRONMENT = Environment(
    account='testing',
    region='testing'
)


def test_match_with_snapshot(snapshot):
    from checkfiles_runner.stacks.runner import RunCheckfilesStepFunction
    from checkfiles_runner.stacks.runner import RunCheckfilesStepFunctionProps

    test_props = RunCheckfilesStepFunctionProps(
        ami_id='ami-testing',
        instance_name='testing',
        instance_profile_arn=INSTANCE_PROFILE_ARN,
        instance_security_group_id='sg-123456',
        checkfiles_tag='main',
        portal_secrets_arn=PORTAL_SECRETS_ARN,
        backend_uri='testing-uri',
    )

    app = App()
    stack = RunCheckfilesStepFunction(
        app,
        'RunCheckfilesStepFunction',
        props=test_props,
        env=ENVIRONMENT,
    )
    template = Template.from_stack(stack)
    snapshot.assert_match(
        json.dumps(
            template.to_json(),
            indent=4,
            sort_keys=True
        ),
        'runner_stack_template.json'
    )
