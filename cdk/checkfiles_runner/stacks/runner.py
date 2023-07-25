from aws_cdk import Duration
from aws_cdk import Environment
from aws_cdk import Stack

from aws_cdk.aws_lambda_python_alpha import PythonFunction
from aws_cdk.aws_lambda_python_alpha import Runtime

from aws_cdk.aws_iam import PolicyStatement
from aws_cdk.aws_iam import Role

from constructs import Contstruct

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
