import base64
import boto3


def lamdba_handler(event, context):
    # event that triggers step function will provide:
    # instance name: name
    # ami id: ami_id
    # instance type: instance_type
    name = event['name']
    # clone checkfiles code and build the virtual environment
    user_data = '''#!/bin/bash
    cd /home/ubuntu
    git clone https://github.com/IGVF-DACC/checkfiles.git
    cd checkfiles
    python3 -m venv venv
    source venv/bin/activate
    pip install -r src/checkfiles/requirements.txt
    cd ..
    chown -R ubuntu:ubuntu checkfiles/
    '''

    ec2 = boto3.resource('ec2')

    boot_disk_volume = {
        'DeviceName': '/dev/sda1',
        'Ebs': {
            'DeleteOnTermination': True,
            'Encrypted': False,
            'VolumeSize': 60,
            'VolumeType': 'gp2',
        }
    }

    instances = ec2.create_instances(
        MinCount=1,
        MaxCount=1,
        BlockDeviceMappings=[boot_disk_volume],
        InstanceType='t2.micro',
        ImageId='ami-09ef01362aa786ed0',
        SecurityGroupIds=['sg-045780345c2bdc6d4'],
        IamInstanceProfile={
            'Arn': 'arn:aws:iam::920073238245:instance-profile/checkfiles-instance'
        },
        UserData=user_data,
    )

    instance = instances[0]

    instance.wait_until_running()

    return {**event, 'instance_id': instance.id}
