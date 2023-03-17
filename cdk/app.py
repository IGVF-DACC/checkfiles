#!/usr/bin/env python3
import os


from aws_cdk import App
from aws_cdk import Environment
from aws_cdk import Stack
from aws_cdk import Duration

from aws_cdk.aws_sqs import Queue

from aws_cdk.aws_lambda import Code
from aws_cdk.aws_lambda import FunctionProps
from aws_cdk.aws_lambda import Runtime

from aws_cdk.aws_lambda_python_alpha import PythonFunction

from aws_cdk.aws_secretsmanager import Secret

from constructs import Construct

from typing import Any

IGVF_DEV_ENV = Environment(account='109189702753', region='us-west-2')
PORTAL_SECRETS_ARN = 'arn:aws:secretsmanager:us-west-2:109189702753:secret:testingcheckfiles-bb38pj' 
PORTAL_API_URL = 'https://api.sandbox.igvf.org'
class CheckFilesStack(Stack):

    def __init__(
            self,
            scope: Construct,
            construct_id: str,
            **kwargs: Any
    ) -> None:
        super().__init__(scope, construct_id, **kwargs)


        pending_files_queue = Queue(
            self,
            'PendingFilesQueue',
            visibility_timeout=Duration.seconds(600),
            queue_name='PendingFilesQueue'
        )


        get_pending_files_lambda = PythonFunction(
            self,
            'PendingFilesToSQSLambda',
            entry='lambda/get_pending_files',
            runtime=Runtime.PYTHON_3_9,
            index='main.py',
            handler='put_pending_files',
            timeout=Duration.seconds(60),
            environment={
                'SQS_QUEUE_URL': pending_files_queue.queue_url,
                'PORTAL_SECRETS_ARN': PORTAL_SECRETS_ARN,
                'PORTAL_URL': PORTAL_API_URL
            }
        )

        pending_files_queue.grant_send_messages(get_pending_files_lambda)
        portal_secrets = Secret.from_secret_complete_arn(
            self,
            id='PortalSecrets',
            secret_complete_arn=PORTAL_SECRETS_ARN
        )
        portal_secrets.grant_read(get_pending_files_lambda)
app = App()
pending_files_to_sqs = CheckFilesStack(app, 'CheckFilesStack', env=IGVF_DEV_ENV)
app.synth()
