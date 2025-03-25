import logging


import boto3


logging.basicConfig(
    level=logging.INFO,
    force=True
)


def get_checkfiles_command_status(event, context):
    ssm = boto3.client('ssm')
    instance_id = event['instance_id']
    command_id = event['command_id']
    iterator = event['iterator']

    result = ssm.get_command_invocation(
        CommandId=command_id,
        InstanceId=instance_id
    )

    command_status = result['Status']

    logging.info(
        f'Command {command_id} on instance {instance_id} in status {command_status}.')
    return {
        'instance_id': instance_id,
        'checkfiles_command_status': command_status,
        'command_id': command_id,
        'instance_id_list': [instance_id],
        'in_progress': command_status == 'InProgress',
        'iterator': iterator
    }
