"""Bucket 3 PoC: validate a remote bigBed (or bigInteract) with pyBigWig range requests.

Same approach as validate_bigwig.py: bigBed is an indexed binary format that seeks
immediately, so it cannot be streamed through a FIFO into `validateFiles -type=bigBed*`
(that dies on `lseek`). pyBigWig over https fetches only the header, the chromosome
list, the index and the entries actually probed -- no download.

bigInteract opens as a bigBed, so the same function covers it; an optional autoSql
comparison (`bb.SQL()` vs src/schemas/as/interact.as) is the one thing validateFiles'
`-as=` check does that this does not. bigInteract still has no portal data.

Private bucket: pyBigWig only speaks https, so an `s3://` URL in a private bucket is
turned into a presigned URL with the given AWS profile (read-only). In production the
task role would presign the same way; the public-bucket path stays the region-explicit
https URL, as for bigWig.

Function body is the `validate_bigbed` sketch from the hand-off doc, now actually run.
Returns a list of error strings ([] = valid).
"""
import os

import boto3
import pyBigWig

S3_REGION = 'us-west-2'


def s3_to_url(url, profile=None, region=S3_REGION, expires=900):
    """s3://BUCKET/KEY -> https. With a profile, a presigned URL (private bucket);
    without, the region-explicit public endpoint."""
    if not url.startswith('s3://'):
        return url
    bucket, _, key = url[len('s3://'):].partition('/')
    if profile:
        s3 = boto3.Session(profile_name=profile).client(
            's3', region_name=region)
        return s3.generate_presigned_url(
            'get_object', Params={'Bucket': bucket, 'Key': key}, ExpiresIn=expires)
    return f'https://{bucket}.s3.{region}.amazonaws.com/{key}'


def validate_bigbed(url, chrom_sizes_path, profile=None):
    """Validate a remote bigBed / bigInteract (bigInteract opens as bigBed)."""
    url = s3_to_url(url, profile=profile)
    errors = []
    if not getattr(pyBigWig, 'remote', 0):
        return ['pyBigWig not built with libcurl (pyBigWig.remote == 0)']

    chrom_sizes = {}
    with open(chrom_sizes_path) as f:
        for line in f:
            if line.strip():
                name, length = line.split()[:2]
                chrom_sizes[name] = int(length)

    try:
        bb = pyBigWig.open(url)
    except (RuntimeError, OSError) as e:
        return [f'could not open as bigBed: {e}']
    if bb is None:
        return ['open() returned None (not found / unreadable)']
    try:
        if not bb.isBigBed():
            errors.append('not a bigBed')
        if (bb.header() or {}).get('nBasesCovered', 0) <= 0:
            errors.append('header reports zero bases covered')
        chroms = bb.chroms() or {}
        if not chroms:
            errors.append('no chromosomes')
        for c, length in chroms.items():
            if c not in chrom_sizes:
                errors.append(f'chrom {c} not in chrom.sizes')
            elif length != chrom_sizes[c]:
                errors.append(f'chrom {c} length {length} != {chrom_sizes[c]}')
        # entries() is the bigBed analog of stats(); wider window since features are sparse.
        # An empty result is NOT an error (no features in range); only an exception is.
        for name, length in sorted(chroms.items(), key=lambda kv: kv[1], reverse=True)[:3]:
            for lo, hi in [(0, min(1_000_000, length)), (max(0, length - 1_000_000), length)]:
                if hi > lo:
                    try:
                        bb.entries(name, lo, hi)
                    except Exception as e:
                        errors.append(f'read failed {name}:{lo}-{hi}: {e}')
    finally:
        bb.close()
    return errors


if __name__ == '__main__':
    import time
    GRCH38 = 'src/schemas/genome_builds/chrom_sizes/GRCh38.chrom.sizes'
    MM39 = 'src/schemas/genome_builds/chrom_sizes/mm39.chrom.sizes'
    # unreleased object in the private bucket: needs a read-only profile to presign
    PROFILE = os.environ.get('SPIKE_AWS_PROFILE', 'prod-read-only-cdk')
    BIGBED = ('s3://igvf-private/2026/08/27/e4e2dfe7-faf1-49fe-b7cd-e0a45e00272e/'
              'IGVFFI7693ROCN.bigBed')
    cases = [
        ('GOOD  bigBed (narrowPeak bed6+4, GRCh38) 161 KB IGVFFI7693ROCN vs GRCh38.chrom.sizes',
         BIGBED, GRCH38, PROFILE),
        ('BAD   same bigBed vs mm39.chrom.sizes (wrong assembly)',
         BIGBED, MM39, PROFILE),
        ('BAD   bigWig posing as bigBed IGVFFI4381NFYZ',
         's3://igvf-public/2026/05/07/fac6e773-ae1c-487a-ae9d-c5af72c91046/IGVFFI4381NFYZ.bigWig',
         GRCH38, None),
        ('BAD   bam posing as bigBed IGVFFI3323DCKT',
         's3://igvf-public/2026/06/10/155918fc-8dc2-4f25-8c1e-9d3fdfb07bc9/IGVFFI3323DCKT.bam',
         GRCH38, None),
        ('BAD   nonexistent key in the private bucket',
         's3://igvf-private/2026/08/27/e4e2dfe7-faf1-49fe-b7cd-e0a45e00272e/NOSUCHFILE.bigBed',
         GRCH38, PROFILE),
    ]
    for label, url, cs, profile in cases:
        t0 = time.time()
        errs = validate_bigbed(url, cs, profile=profile)
        shown = errs if len(
            errs) <= 4 else errs[:4] + [f'... (+{len(errs)-4} more)']
        print(f'{label}\n   -> {shown}  ({time.time()-t0:.1f}s)\n')
