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

from aws_cdk.aws_ecs import AwsLogDriverMode
from aws_cdk.aws_ecs import ICluster
from aws_cdk.aws_ecs import ContainerImage
from aws_cdk.aws_ecs import DeploymentCircuitBreaker
from aws_cdk.aws_ecs import Secret
from aws_cdk.aws_ecs import LogDriver

from aws_cdk.aws_ecs_patterns import QueueProcessingFargateService

from aws_cdk.aws_lambda_python_alpha import PythonFunction

from aws_cdk.aws_secretsmanager import Secret as SMSecret

from aws_cdk.aws_applicationautoscaling import ScalingInterval

from constructs import Construct

from typing import Any
from typing import List

from dataclasses import dataclass
from dataclasses import field

@dataclass
class CheckFilesServiceProps:
    cpu: int
    portal_secrets_complete_arn: str
    memory_limit_mib: int
    min_scaling_capacity: int
    max_scaling_capacity: int
    scaling_steps: List[ScalingInterval] = field(
        default_factory=lambda: [
            ScalingInterval(
                upper=0,
                change=-1,
            ),
            ScalingInterval(
                lower=1,
                change=1,
            ),
            ScalingInterval(
                lower=1000,
                change=2,
            ),
        ]
    )

IGVF_DEV_ENV = Environment(account='109189702753', region='us-west-2')
PORTAL_SECRETS_ARN = 'arn:aws:secretsmanager:us-west-2:109189702753:secret:testingcheckfiles-bb38pj'
PORTAL_API_URL = 'https://api.sandbox.igvf.org'
checkfilesserviceprops = CheckFilesServiceProps(
        portal_secrets_complete_arn=PORTAL_SECRETS_ARN,
        cpu=256,
        memory_limit_mib=512,
        min_scaling_capacity=1,
        max_scaling_capacity=2,
)



class CheckFilesStack(Stack):

    def __init__(
            self,
            scope: Construct,
            construct_id: str,
            props: CheckFilesServiceProps,
            **kwargs: Any
    ) -> None:
        super().__init__(scope, construct_id, **kwargs)
        self.props = props


        self.portal_secrets = SMSecret.from_secret_complete_arn(
            self,
            id='PortalSecrets',
            secret_complete_arn=self.props.portal_secrets_complete_arn
        )

        self.pending_files_queue = Queue(
            self,
            'PendingFilesQueue',
            visibility_timeout=Duration.seconds(600),
            queue_name='PendingFilesQueue'
        )


        self.get_pending_files_lambda = PythonFunction(
            self,
            'PendingFilesToSQSLambda',
            entry='lambda/get_pending_files',
            runtime=Runtime.PYTHON_3_9,
            index='main.py',
            handler='put_pending_files',
            timeout=Duration.seconds(60),
            environment={
                'SQS_QUEUE_URL': self.pending_files_queue.queue_url,
                'PORTAL_SECRETS_ARN': PORTAL_SECRETS_ARN,
                'PORTAL_URL': PORTAL_API_URL
            }
        )

        self.checkfiles_service = QueueProcessingFargateService(
            self,
            'CheckfilesService',
            service_name='CheckfilesService',
            image=ContainerImage.from_asset(
                '../',
                file='docker/Dockerfile',
            ),
            queue=self.pending_files_queue,
            cpu=self.props.cpu,
            memory_limit_mib=self.props.memory_limit_mib,
            min_scaling_capacity=self.props.min_scaling_capacity,
            max_scaling_capacity=self.props.max_scaling_capacity,
            scaling_steps=self.props.scaling_steps,
            enable_execute_command=True,
            circuit_breaker=DeploymentCircuitBreaker(
                rollback=True,
            ),
            command=['python', '/checkfiles/read_from_queue.py'],
            log_driver=LogDriver.aws_logs(
                stream_prefix='checkfiles-service',
                mode=AwsLogDriverMode.NON_BLOCKING,
            ),
            environment={
                'PENDING_FILES_QUEUE_URL': self.pending_files_queue.queue_url
            },
            secrets={
                'IGVF_PORTAL_KEY': Secret.from_secrets_manager(
                    self.portal_secrets,
                    'IGVF_PORTAL_KEY',
                ),
                'IGVF_PORTAL_SECRET_KEY': Secret.from_secrets_manager(
                    self.portal_secrets,
                    'IGVF_PORTAL_SECRET_KEY',
                )
            }
        )

        self.pending_files_queue.grant_consume_messages(self.checkfiles_service.task_definition.task_role)
        self.pending_files_queue.grant_send_messages(self.get_pending_files_lambda)
        self.portal_secrets.grant_read(self.get_pending_files_lambda)
app = App()
pending_files_to_sqs = CheckFilesStack(app, 'CheckFilesStack', props=checkfilesserviceprops, env=IGVF_DEV_ENV)
app.synth()
