config = {
    'region': 'us-west-2',
    'account_staging': '920073238245',  # igvf-staging
    'account_production': '035226225042',  # igvf-prod
    'ami_id_sandbox': 'ami-0e5624e85a6684ff1',
    'ami_id_production': 'ami-0af99db6419744f44',
    'portal_secrets_arn_sandbox': 'arn:aws:secretsmanager:us-west-2:920073238245:secret:checkfiles-portal-secret-u9aeGR',
    'portal_secrets_arn_production': 'arn:aws:secretsmanager:us-west-2:035226225042:secret:checkfiles-portal-secret-GWpoIK',
    'instance_type_sandbox': 't2.2xlarge',
    'instance_type_production': 't2.xlarge',
    'instance_name_sandbox': 'checkfiles-sandbox',
    'instance_name_production': 'checkfiles-production',
    'instance_profile_arn_sandbox': 'arn:aws:iam::920073238245:instance-profile/checkfiles-instance',
    'instance_profile_arn_production': 'arn:aws:iam::035226225042:instance-profile/checkfiles-instance',
    'instance_security_group_sandbox': 'sg-045780345c2bdc6d4',
    'instance_security_group_production': 'sg-0136bee948bf49fe7',
    'backend_uri_sandbox': 'https://api.sandbox.igvf.org',
    'backend_uri_production': 'https://api.data.igvf.org',
    'checkfiles_branch_sandbox': 'main',
    'checkfiles_branch_production': 'main',
}
