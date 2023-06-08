# Checkfiles

[![CircleCI](https://circleci.com/gh/IGVF-DACC/checkfiles/tree/main.svg?style=svg)](https://circleci.com/gh/IGVF-DACC/checkfiles/tree/main)
[![Coverage Status](https://coveralls.io/repos/github/IGVF-DACC/checkfiles/badge.svg?branch=main&kill_cache=1)](https://coveralls.io/github/IGVF-DACC/checkfiles?branch=main)

Checkfiles is used to check new or updated files in AWS S3 bucket to see if the size and MD5 sum (both for gzipped and ungzipped) are identical to the submitted metadata. It also checks some other properties for specific file type.

Checks for all files:

- File size
- MD5 sum
- Should the file be zipped
- Content MD5 sum if the file is zipped

Additional checks for BAM file:

- Is the file a valid BAM file by pysam
- Is the file sorted
- The number of reads
- Generate index file for this BAM file

Additional checks for BED, BEDPE, BIGBED, BIGINTERACT and BIGWIG files:

- Is the file a valid file by validateFiles

Additional checks for FASTA file:

- Is the file a valid FASTA file by py_fasta_validator

Additional checks for FASTQ file:

- The number of reads
- Mean Read length
- Minimum Read length
- Maximum Read length

## File types for validation

- BAM
- BED
- BEDPE
- BIGBED
- BIGINTERACT
- BIGWIG
- FASTQ
- FASTA
- TXT
- TSV


## Usage:

```bash
$ python src/checkfiles/checkfiles.py -h
usage: checkfiles.py [-h] [--uuid UUID] [--server SERVER] [--portal-key-id PORTAL_KEY_ID] [--portal-secret-key PORTAL_SECRET_KEY] [--patch] [--ignore-active-credentials]

Checkfiles argumentparser

optional arguments:
  -h, --help            show this help message and exit
  --uuid UUID           UUID of the fileobject to be checked.
  --server SERVER       igvf instance to check. https://api.sandbox.igvf.org for example
  --portal-key-id PORTAL_KEY_ID
                        Portal key id
  --portal-secret-key PORTAL_SECRET_KEY
                        Portal secret key
  --patch               Patch the checked objects.
  --ignore-active-credentials
                        If this flag is set, then we omit checking if the file has unexpired upload credentials. There be dragons here, someone might change the underlying file after checking.
```

Note that if `uuid` flag is not set, all the files with `upload_status=pending` will be checked. It may be prudent to use `screen` to run because the job can take several hours.

## Running checkfiles on EC2

In order to deploy a checkfiles EC2 instance (right now it makes most sense to run on igvf-staging account, to easily have access both to sandbox and prod from same machine).
1. Log into igvf-staging aws console.
2. Go to EC2 console and in the left tab select `AMIs`
3. Select the newest `checkfiles__ami` (`ami-02001e7412122509a`)
4. Click `Launch instance from AMI`.
5. Select instance type, and add storage. 200GB should be enough for anything. Instance size depends on the resource requirements. For instance type, t2 family of general purpose instances is good.
6. Under `Advanced details` IAM instance profile, attach `checkfiles-instance` profile to the machine.
7. Deploy. Select "Proceed without key pair" Wait for the machine to come up.
8. Connect to the machine using https://pypi.org/project/ec2instanceconnectcli/
9. On the machine clone this repo into the home directory of the default ubuntu user:
```bash
$ git clone https://github.com/IGVF-DACC/checkfiles.git
```

To run checkfiles on the instance prepared above:
1. Build the python environment and activate:
```
$ cd checkfiles
$ python3 -m venv venv
$ source venv/bin/activate
$ pip install -r src/checkfiles/requirements.txt
```

2. Run (for example for uuid=`my_file_uuid` on sandbox):
```
venv/bin/python src/checkfiles/checkfiles.py --server https://api.sandbox.igvf.org --portal-key-id portal_key_id --portal-secret-key my_secret_key --uuid my_file_uuid
```

## Testing

1. Download `validateFiles` from http://hgdownload.cse.ucsc.edu/admin/exe/. If you are running on M1 mac, the file you want is http://hgdownload.cse.ucsc.edu/admin/exe/macOSX.arm64/validateFiles. Make sure `validateFiles` is available in your `$PATH`.
2. Create a virtualenvironment and install requirements from `src/checkfiles/requirements.txt`.
3. Run tests with `pytest`
