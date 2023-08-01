import boto3


def run_checkfiles_command(event, context):
    instance_id = event['instance_id']
    ssm = boto3.client('ssm')
    response = ssm.send_command(
        InstanceIds=[instance_id],
        DocumentName='AWS-RunShellScript',
        Parameters={'commands': [
            'sleep 60',
            'echo "Hello World" > /home/ubuntu/foo.txt',
            'exit 1'
        ]
        }
    )

    return {'instance_id': instance_id, 'command_id': response['Command']['CommandId']}
