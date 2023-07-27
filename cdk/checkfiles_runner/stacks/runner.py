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
            **kwargs: Any
    ) -> None:
        super().__init__(scope, construct_id, **kwargs)
        self.ami_id = ami_id
        self.instance_type = instance_type
        self.instance_name = instance_name

        create_checkfiles_instance_lambda = PythonFunction(
            self,
            'CreateCheckfilesInstanceLambda',
            entry='checkfiles_runner/lambdas/create_instance',
            runtime=Runtime.PYTHON_3_9,
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

        run_checkfiles_command_lambda = PythonFunction(
            self,
            'RunCheckfilesCommandLambda',
            entry='checkfiles_runner/lambdas/run_checkfiles',
            runtime=Runtime.PYTHON_3_9,
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

        definition = create_checkfiles_instance.next(
            run_checkfiles_command
        )

        state_machine = StateMachine(
            self,
            'StateMachine',
            definition=definition
        )
