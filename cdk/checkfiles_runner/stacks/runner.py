from aws_cdk import Duration
from aws_cdk import Environment
from aws_cdk import Stack

from aws_cdk.aws_lambda_python_alpha import PythonFunction
from aws_cdk.aws_lambda import Runtime

from aws_cdk.aws_iam import PolicyStatement
from aws_cdk.aws_iam import Role

from constructs import Construct

from aws_cdk.aws_events import Rule
from aws_cdk.aws_events import Schedule

from aws_cdk.aws_events_targets import SfnStateMachine

from aws_cdk.aws_secretsmanager import Secret as SMSecret

from aws_cdk.aws_stepfunctions import JsonPath
from aws_cdk.aws_stepfunctions import Pass
from aws_cdk.aws_stepfunctions import Succeed
from aws_cdk.aws_stepfunctions import StateMachine
from aws_cdk.aws_stepfunctions import TaskInput
from aws_cdk.aws_stepfunctions import Wait
from aws_cdk.aws_stepfunctions import WaitTime
from aws_cdk.aws_stepfunctions import Fail

from aws_cdk.aws_stepfunctions_tasks import LambdaInvoke

from typing import Any


class RunCheckfilesStepFunction(Stack):

    def __init__(
            self,
            scope: Construct,
            construct_id: str,
            ami_id: str,
            instance_type: str,
            instance_name: str,
            portal_secrets_arn: str,
            backend_uri: str,
            **kwargs: Any
    ) -> None:
        super().__init__(scope, construct_id, **kwargs)
        self.ami_id = ami_id
        self.instance_type = instance_type
        self.instance_name = instance_name
        self.portal_secrets_arn = portal_secrets_arn
        self.backend_uri = backend_uri

        self.portal_secrets = SMSecret.from_secret_complete_arn(
            self,
            id='PortalSecrets',
            secret_complete_arn=self.portal_secrets_arn
        )

        check_pending_files_lambda = PythonFunction(
            self,
            'CheckPendingFilesLambda',
            entry='checkfiles_runner/lambdas/check_pending',
            runtime=Runtime.PYTHON_3_11,
            index='main.py',
            handler='check_pending_files',
            timeout=Duration.seconds(30),
            environment={
                'PORTAL_SECRETS_ARN': self.portal_secrets_arn,
                'BACKEND_URI': self.backend_uri
            }
        )

        self.portal_secrets.grant_read(check_pending_files_lambda)

        check_pending_files = LambdaInvoke(
            self,
            'CheckPendingFiles',
            lambda_function=check_pending_files_lambda,
            payload_response_only=True,
            result_selector={
                'files_pending.$': '$.files_pending'
            }
        )

        create_checkfiles_instance_lambda = PythonFunction(
            self,
            'CreateCheckfilesInstanceLambda',
            entry='checkfiles_runner/lambdas/create_instance',
            runtime=Runtime.PYTHON_3_11,
            index='main.py',
            handler='create_checkfiles_instance',
            timeout=Duration.seconds(360),
            environment={
                'AMI_ID': self.ami_id,
                'INSTANCE_TYPE': self.instance_type,
                'INSTANCE_NAME': self.instance_name,
            }
        )

        create_checkfiles_instance_lambda.add_to_role_policy(
            PolicyStatement(
                actions=[
                    'iam:PassRole',
                ],
                resources=['*'],
            )
        )

        create_checkfiles_instance_lambda.add_to_role_policy(
            PolicyStatement(
                actions=[
                    'ec2:RunInstances',
                    'ec2:AssociateIamInstanceProfile',
                    'ec2:ModifyInstanceAttribute',
                    'ec2:CreateVolume',
                    'ec2:AttachVolume',
                    'ec2:CreateTags',
                    'ec2:DescribeInstances',
                    'ec2:ReportInstanceStatus',
                ],
                resources=['*'],
            )
        )

        create_checkfiles_instance = LambdaInvoke(
            self,
            'CreateCheckfilesInstance',
            lambda_function=create_checkfiles_instance_lambda,
            payload_response_only=True,
            result_selector={
                'create_checkfiles_instance.$': '$'
            }
        )

        wait_instance_ssm_registration = Wait(
            self,
            'WaitForSSMReg',
            time=WaitTime.duration(
                Duration.minutes(2)
            )
        )

        run_checkfiles_command_lambda = PythonFunction(
            self,
            'RunCheckfilesCommandLambda',
            entry='checkfiles_runner/lambdas/run_checkfiles',
            runtime=Runtime.PYTHON_3_11,
            index='main.py',
            handler='run_checkfiles_command',
            timeout=Duration.seconds(60),
        )

        run_checkfiles_command_lambda.add_to_role_policy(
            PolicyStatement(
                actions=[
                    'ssm:SendCommand',
                    'ssm:GetCommandInvocation',
                ],
                resources=['*'],
            )
        )

        run_checkfiles_command = LambdaInvoke(
            self,
            'RunCheckFilesCommand',
            lambda_function=run_checkfiles_command_lambda,
            payload_response_only=True,
            result_selector={
                'run_checkfiles_command.$': '$'
            }
        )

        wait_for_checkfiles_lambda = PythonFunction(
            self,
            'WaitForCheckfilesLambda',
            entry='checkfiles_runner/lambdas/wait_checkfiles',
            runtime=Runtime.PYTHON_3_11,
            index='main.py',
            handler='wait_checkfiles_command_to_finish',
            timeout=Duration.seconds(180),
        )

        wait_for_checkfiles_lambda.add_to_role_policy(
            PolicyStatement(
                actions=[
                    'ssm:GetCommandInvocation'
                ],
                resources=['*'],
            )
        )

        wait_for_checkfiles = LambdaInvoke(
            self,
            'WaitForCheckfiles',
            lambda_function=wait_for_checkfiles_lambda,
            payload_response_only=True,
            result_selector={
                'checkfiles_command_status.$': '$'
            }
        )

        definition = check_pending_files.next(
            create_checkfiles_instance
        ).next(
            wait_instance_ssm_registration
        ).next(
            run_checkfiles_command
        ).next(
            wait_for_checkfiles
        )

        state_machine = StateMachine(
            self,
            'StateMachine',
            definition=definition
        )