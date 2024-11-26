import os
import logging

import boto3


logging.basicConfig(
    level=logging.INFO,
    force=True
)


def get_ami_id():
    return os.environ['AMI_ID']


def get_instance_name():
    return os.environ['INSTANCE_NAME']


def get_instance_profile_arn():
    return os.environ['INSTANCE_PROFILE_ARN']


def get_security_group():
    return os.environ['SECURITY_GROUP']


def get_checkfiles_tag():
    return os.environ['CHECKFILES_TAG']


def get_instance_type_from_number_of_files_pending(number_of_files_pending: int):
    if number_of_files_pending <= 2:
        return 'c6a.large'
    elif number_of_files_pending <= 4:
        return 'c6a.xlarge'
    elif number_of_files_pending <= 8:
        return 'c6a.2xlarge'
    elif number_of_files_pending <= 16:
        return 'c6a.4xlarge'
    else:
        return 'c6a.8xlarge'


def create_checkfiles_instance(event, context):
    number_of_files_pending = event['number_of_files_pending']
    instance_name = get_instance_name()
    ami_id = get_ami_id()
    instance_type = get_instance_type_from_number_of_files_pending(
        number_of_files_pending)
    instance_profile_arn = get_instance_profile_arn()
    security_group = get_security_group()
    tag = get_checkfiles_tag()
    # clone checkfiles code and build the virtual environment
    user_data = f'''#!/bin/bash
    cd /home/ubuntu
    git clone https://github.com/IGVF-DACC/checkfiles.git --branch {tag} --single-branch
    cd checkfiles
    python3 -m venv venv
    source venv/bin/activate
    pip install -r src/checkfiles/requirements.txt
    python src/checkfiles/utils/download_ref_files.py
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

    logging.info(
        f'instance_type: {instance_type} ami_id: {ami_id} checkfiles_tag: {tag}')
    logging.info(f'user_data: \n {user_data}')

    instances = ec2.create_instances(
        MinCount=1,
        MaxCount=1,
        BlockDeviceMappings=[boot_disk_volume],
        InstanceType=instance_type,
        ImageId=ami_id,
        SecurityGroupIds=[security_group],
        IamInstanceProfile={
            'Arn': instance_profile_arn
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

    return {'instance_id': instance.id,
            'instance_type': instance.instance_type,
            }
