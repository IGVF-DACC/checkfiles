import boto3


def wait_checkfiles_command_to_finish(event, context):
    ssm = boto3.client('ssm')
    instance_id = event['run_checkfiles_command']['create_checkfiles_instance']['instance_id']
    command_id = event['run_checkfiles_command']['command_id']
    waiter = ssm.get_waiter('command_executed')

    waiter.wait(
        CommandId=command_id,
        InstanceId=instance_id,
        WaiterConfig={
            'Delay': 10,
            'MaxAttempts': 15
        }
    )

    result = ssm.get_command_invocation(
        CommandId=command_id,
        InstanceId=instance_id
    )

    command_status = result['Status']

    return {**event, 'checkfiles_command_status': command_status}
