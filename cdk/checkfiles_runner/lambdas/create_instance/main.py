import os
import base64
import boto3


def get_ami_id():
    return os.environ['AMI_ID']


def get_instance_name():
    return os.environ['INSTANCE_NAME']


def get_instance_type():
    return os.environ['INSTANCE_TYPE']


def create_checkfiles_instance(event, context):
    instance_name = get_instance_name()
    ami_id = get_ami_id()
    instance_type = get_instance_type()
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
        InstanceType=instance_type,
        ImageId=ami_id,
        SecurityGroupIds=['sg-045780345c2bdc6d4'],
        IamInstanceProfile={
            'Arn': 'arn:aws:iam::920073238245:instance-profile/checkfiles-instance'
        },
        UserData=user_data,
        TagSpecifications=[{
            'ResourceType': 'instance',
            'Tags': [{
                'Key': 'Name',
                'Value': instance_name
            }]
        }]
    )

    instance = instances[0]

    instance.wait_until_running()

    return {**event, 'instance_id': instance.id}
