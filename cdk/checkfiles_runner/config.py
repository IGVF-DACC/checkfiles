config = {
    'account': '920073238245',  # igvf-staging
    'region': 'us-west-2',
    'ami_id': 'ami-0e5624e85a6684ff1',
    'portal_secrets_arn': 'arn:aws:secretsmanager:us-west-2:920073238245:secret:checkfiles-portal-secret-u9aeGR',
    'instance_type_sandbox': 't2.2xlarge',
    'instance_type_production': 't2.xlarge',
    'instance_name_sandbox': 'checkfiles-sandbox',
    'instance_name_production': 'checkfiles-production',
    'backend_uri_sandbox': 'https://api.sandbox.igvf.org',
    'backend_uri_production': 'https://api.data.igvf.org',
    'checkfiles_branch_sandbox': 'main',
    'checkfiles_branch_production': 'main',
}
