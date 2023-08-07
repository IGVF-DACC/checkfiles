import logging


import boto3


logging.basicConfig(
    level=logging.INFO,
    force=True
)


class CommandInProgress(Exception):
    pass


def wait_checkfiles_command_to_finish(event, context):
    ssm = boto3.client('ssm')
    instance_id = event['instance_id']
    command_id = event['command_id']

    result = ssm.get_command_invocation(
        CommandId=command_id,
        InstanceId=instance_id
    )

    command_status = result['Status']

    if command_status == 'InProgress':
        logging.info(
            f'Command {command_id} on instance {instance_id} In Progress.')
        raise CommandInProgress
    else:
        logging.info(
            f'Command {command_id} on instance {instance_id} in status {command_status}. Proceeding to terminate the instance')
        return {
            'instance_id': instance_id,
            'checkfiles_command_status': command_status,
            'command_id': command_id,
            'instance_id_list': [instance_id]
        }
