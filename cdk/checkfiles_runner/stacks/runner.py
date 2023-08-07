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

from aws_cdk.aws_stepfunctions import Choice
from aws_cdk.aws_stepfunctions import Condition
from aws_cdk.aws_stepfunctions import JsonPath
from aws_cdk.aws_stepfunctions import Succeed
from aws_cdk.aws_stepfunctions import StateMachine
from aws_cdk.aws_stepfunctions import Wait
from aws_cdk.aws_stepfunctions import WaitTime

from aws_cdk.aws_stepfunctions_tasks import CallAwsService
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
            checkfiles_branch: str,
            portal_secrets_arn: str,
            backend_uri: str,
            **kwargs: Any
    ) -> None:
        super().__init__(scope, construct_id, **kwargs)
        self.ami_id = ami_id
        self.instance_type = instance_type
        self.instance_name = instance_name
        self.checkfiles_branch = checkfiles_branch
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
            output_path='$.files_pending'
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
                'CHECKFILES_BRANCH': self.checkfiles_branch,
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
                'instance_id.$': '$.instance_id'
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
            environment={
                'PORTAL_SECRETS_ARN': self.portal_secrets_arn,
                'BACKEND_URI': self.backend_uri
            }
        )

        self.portal_secrets.grant_read(run_checkfiles_command_lambda)

        run_checkfiles_command_lambda.add_to_role_policy(
            PolicyStatement(
                actions=[
                    'ssm:SendCommand',
                    'ssm:GetCommandInvocation',
                ],
                resources=['*'],
            )
        )

        run_checkfiles_command_lambda.add_to_role_policy(
            PolicyStatement(
                actions=[
                    'logs:CreateLogGroup',
                    'logs:CreateLogStream',
                    'logs:PutLogEvents',
                    'logs:DescribeLogStreams',
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
                'instance_id.$': '$.instance_id',
                'command_id.$': '$.command_id'
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
                'checkfiles_command_status.$': '$.checkfiles_command_status',
                'instance_id.$': '$.instance_id',
                'command_id.$': '$.command_id',
                'instance_id_list.$': '$.instance_id_list'
            }
        )

        wait_for_checkfiles.add_retry(
            backoff_rate=1,
            errors=['CommandInProgress'],
            interval=Duration.seconds(3600),
            max_attempts=22,
        )

        no_files_to_process = Succeed(
            self,
            'No files to process.'
        )

        terminate_instance = CallAwsService(
            self,
            'TerminateInstance',
            service='ec2',
            action='terminateInstances',
            iam_resources=['*'],
            parameters={
                'InstanceIds.$': '$.instance_id_list'
            },
            result_path=JsonPath.DISCARD,
        )

        definition = check_pending_files.next(
            Choice(self, 'Pending files?').when(
                Condition.boolean_equals('$', False), no_files_to_process
            ).otherwise(
                create_checkfiles_instance.next(
                    wait_instance_ssm_registration
                ).next(
                    run_checkfiles_command
                ).next(
                    wait_for_checkfiles
                ).next(
                    terminate_instance
                )
            )
        )

        state_machine = StateMachine(
            self,
            'StateMachine',
            definition=definition
        )

        state_machine_target = SfnStateMachine(
            state_machine
        )

        Rule(
            self,
            'RunCheckfilesStateMachineCronRule',
            schedule=Schedule.cron(
                hour='4',
                minute='20',
            ),
            targets=[
                state_machine_target
            ]
        )


class RunCheckfilesStepFunctionSandbox(RunCheckfilesStepFunction):
    pass


class RunCheckfilesStepFunctionProduction(RunCheckfilesStepFunction):
    pass
