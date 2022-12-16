# Checkfiles

[![CircleCI](https://circleci.com/gh/IGVF-DACC/checkfiles/tree/CHECK-15-igvf-checkfiles.svg?style=svg)](https://circleci.com/gh/IGVF-DACC/checkfiles/tree/CHECK-15-igvf-checkfiles)
[![Coverage Status](https://coveralls.io/repos/github/IGVF-DACC/checkfiles/badge.svg?branch=CHECK-15-igvf-checkfiles&kill_cache=1)](https://coveralls.io/github/IGVF-DACC/checkfiles?branch=CHECK-15-igvf-checkfiles)

Checkfiles is used to check new or updated files in google cloud to see if the size and MD5 sum (both for gzipped and ungzipped) are identical to the submitted metadata. It also checks some other properties for specific file type.

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
    -e AWS_ACCESS_KEY_ID=xxxxxxxxx -e AWS_SECRET_ACCESS_KEY=xxxxxxx\
    -v /Users/mingjie/git/igvf/gcsfuse/key.json:/checkfiles/key.json:ro \
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
