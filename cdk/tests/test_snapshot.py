import pytest
import json

from aws_cdk import App
from aws_cdk import Environment

from aws_cdk.assertions import Template


PORTAL_SECRETS_ARN = 'arn:aws:secretsmanager:us-west-2:123456:secret:testing-secret-123456'
ENVIRONMENT = Environment(
    account='testing',
    region='testing'
)


def test_match_with_snapshot(snapshot):
    from checkfiles_runner.stacks.runner import RunCheckfilesStepFunction
    app = App()
    stack = RunCheckfilesStepFunction(
        app,
        'RunCheckfilesStepFunction',
        ami_id='ami-testing',
        instance_type='t2.testing',
        instance_name='testing',
        checkfiles_branch='main',
        portal_secrets_arn=PORTAL_SECRETS_ARN,
        backend_uri='testing-uri',
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
