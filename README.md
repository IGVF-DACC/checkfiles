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


## Running checkfiles on EC2

In order to deploy a checkfiles EC2 instance (right now it makes most sense to run on igvf-staging account, to easily have access both to sandbox and prod from same machine).
1. Log into igvf-staging aws console.
2. Go to EC2 console and in the left tab select `AMIs`
3. Select the newest `checkfiles__ami` (`ami-02001e7412122509a`)
4. Click `Launch instance from AMI`.
5. Select instsance type, and add storage. 200GB should be enough for anything.
6. Under `Advanced details` IAM instance profile, attach `checkfiles-instance` profile to the machine.
7. Deploy. Select "Proceed without key pair" Wait for the machine to come up.
8. Connect to the machine using https://pypi.org/project/ec2instanceconnectcli/
9. On the machine clone this repo into the home directory of the default ubuntu user.

To run checkfiles on the instance prepared above:
1. Build the python environment and activate:
```
$ cd checkfiles
$ python3 -m venv venv
$ source venv/bin/activate
```

2. Run (for example for uuid=`my_file_uuid` on sandbox):
```
venv/bin/python src/checkfiles/checkfiles.py --server https://api.sandbox.igvf.org --portal-key-id portal_key_id --portal-secret-key my_secret_key --uuid my_file_uuid
```



## Run checkfiles in docker

- Build the image

`docker image build -f docker/Dockerfile -t checkfiles .`

- There are some test file examples in file_examples folder. You can use one of them to run the build

```bash
docker run -it --privileged --platform linux/amd64 \
    --env-file src/file_examples/bed_bed3+_env.txt \
    -e AWS_ACCESS_KEY_ID=xxxxxxxx -e AWS_SECRET_ACCESS_KEY=xxxxxxxx\
    -e ENCODE_ACCESS_KEY=xxxxxxxx -e ENCODE_SECRET_KEY=xxxxxxxx\
    checkfiles
```

## Testing

Use the docker image to run test.

```bash
docker run -it --privileged --platform linux/amd64 \
    -e AWS_ACCESS_KEY_ID=xxxxxxxx -e AWS_SECRET_ACCESS_KEY=xxxxxxxx\
    -e ENCODE_ACCESS_KEY=xxxxxxxx -e ENCODE_SECRET_KEY=xxxxxxxx\
    checkfiles pytest
```

To measure the code coverage of your tests, use the coverage command to run pytest instead of running it directly.

```bash
docker run -it --privileged --platform linux/amd64 \
    -e AWS_ACCESS_KEY_ID=xxxxxxxx -e AWS_SECRET_ACCESS_KEY=xxxxxxxx\
    -e ENCODE_ACCESS_KEY=xxxxxxxx -e ENCODE_SECRET_KEY=xxxxxxxx\
    checkfiles coverage run -m pytest && coverage report
```
