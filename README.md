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

`docker image build --platform=amd64 -t checkfiles .`

- Run the build

```bash
docker run --platform linux/amd64  -it  --privileged \
    -v /Users/mingjie/git/igvf/gcsfuse/key.json:/checkfiles/key.json:ro \
    -e ENCODE_ACCESS_KEY={xxxxxxx} -e ENCODE_CECRET_KEY={xxxxxxxxx} \
    checkfiles
```

- if you want to just run bash command in docker

```bash
docker run --platform linux/amd64  -it  --privileged \
    -v /Users/mingjie/git/igvf/gcsfuse/key.json:/checkfiles/key.json:ro \
    checkfiles bash
```
