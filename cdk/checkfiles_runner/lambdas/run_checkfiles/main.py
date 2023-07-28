import boto3


def run_checkfiles_command(event, context):
    instance_id = event['create_checkfiles_instance']['instance_id']
    ssm = boto3.client('ssm')
    response = ssm.send_command(
        InstanceIds=[instance_id],
        DocumentName='AWS-RunShellScript',
        Parameters={'commands': [
            'echo "Hello World" > /home/ubuntu/foo.txt'
        ]
        }
    )

    return {**event, 'command_id': response['Command']['CommandId']}
