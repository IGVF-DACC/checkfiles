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

- Is the file a valid BAM file by SamtoolsError
- Is the file sorted
- The number of reads
- Generate index file for this BAM file

Additional checks for FASTQ file:

- The number of reads
- Read length

## File types for validation

- FASTQ
- BAM
- TXT
- TSV

## Run checkfiles in docker

- Build the image

`docker image build -t checkfiles .`

- Run the build

```bash
docker run -it --privileged \
    -e AWS_ACCESS_KEY_ID=xxxxxxxx -e AWS_SECRET_ACCESS_KEY=xxxxxxxx\
    -e ENCODE_ACCESS_KEY=xxxxxxxx -e ENCODE_CECRET_KEY=xxxxxxxx\
    checkfiles
```

## Local test

To run the tests, use the pytest command.

`pytest`

To measure the code coverage of your tests, use the coverage command to run pytest instead of running it directly.

`coverage run -m pytest`

An HTML report allows you to see which lines were covered in each file:

`coverage html`

This generates files in the htmlcov directory. Open htmlcov/index.html in your browser to see the report.
