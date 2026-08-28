"""Bucket 3 PoC: validate a remote bigWig with pyBigWig range requests (no download).

This replaces `validateFiles -type=bigWig`, which cannot be streamed at all: it is an
indexed binary format and seeks immediately (`lseek(0, -4, SEEK_END) failed` on a FIFO).
pyBigWig over https uses libcurl range requests and touches only the header, the index,
and the intervals actually probed.

Function body is the one from the hand-off doc, unchanged apart from the s3->https helper.
Returns a list of error strings ([] = valid).
"""
import pyBigWig

S3_REGION = 'us-west-2'


def s3_to_https(url, region=S3_REGION):
    """Region-explicit endpoint: the global BUCKET.s3.amazonaws.com form can 301 and
    libcurl will not always follow it."""
    if not url.startswith('s3://'):
        return url
    bucket, _, key = url[len('s3://'):].partition('/')
    return f'https://{bucket}.s3.{region}.amazonaws.com/{key}'


def validate_bigwig(url, chrom_sizes_path):
    """Validate a remote bigWig via range requests. Returns list of errors ([] = valid)."""
    url = s3_to_https(url)
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
        bw = pyBigWig.open(url)
    except (RuntimeError, OSError) as e:
        return [f'could not open as bigWig: {e}']
    if bw is None:
        return ['open() returned None (not found / unreadable)']
    try:
        if not bw.isBigWig():
            errors.append('not a bigWig')
        if (bw.header() or {}).get('nBasesCovered', 0) <= 0:
            errors.append('header reports zero bases covered')
        chroms = bw.chroms() or {}
        if not chroms:
            errors.append('no chromosomes')
        for c, length in chroms.items():
            if c not in chrom_sizes:
                errors.append(f'chrom {c} not in chrom.sizes')
            elif length != chrom_sizes[c]:
                errors.append(f'chrom {c} length {length} != {chrom_sizes[c]}')
        # exercise index + last data blocks at start AND end of the biggest chroms
        for name, length in sorted(chroms.items(), key=lambda kv: kv[1], reverse=True)[:3]:
            for lo, hi in [(0, min(10_000, length)), (max(0, length - 10_000), length)]:
                if hi > lo:
                    try:
                        bw.stats(name, lo, hi, type='mean', nBins=1)
                    except Exception as e:
                        errors.append(f'read failed {name}:{lo}-{hi}: {e}')
    finally:
        bw.close()
    return errors


if __name__ == '__main__':
    import time
    GRCH38 = 'src/schemas/genome_builds/chrom_sizes/GRCh38.chrom.sizes'
    MM39 = 'src/schemas/genome_builds/chrom_sizes/mm39.chrom.sizes'
    cases = [
        ('GOOD  bigWig GRCh38 30 MB IGVFFI4381NFYZ vs GRCh38.chrom.sizes',
         's3://igvf-public/2026/05/07/fac6e773-ae1c-487a-ae9d-c5af72c91046/IGVFFI4381NFYZ.bigWig', GRCH38),
        ('GOOD  bigWig GRCh38 502 MB IGVFFI3803JOCY vs GRCh38.chrom.sizes',
         's3://igvf-public/2026/05/07/fd04d5c7-947a-4c3a-8dfd-2257d1c0554e/IGVFFI3803JOCY.bigWig', GRCH38),
        ('BAD   same GRCh38 bigWig vs mm39.chrom.sizes (wrong assembly)',
         's3://igvf-public/2026/05/07/fac6e773-ae1c-487a-ae9d-c5af72c91046/IGVFFI4381NFYZ.bigWig', MM39),
        ('GOOD  bigWig GRCm39 875 MB IGVFFI5621HHJK vs mm39.chrom.sizes',
         's3://igvf-public/2025/10/11/fd306b94-a7c5-4e68-8cf4-42336b3568a2/IGVFFI5621HHJK.bigWig', MM39),
        ('BAD   bam posing as bigWig IGVFFI3323DCKT',
         's3://igvf-public/2026/06/10/155918fc-8dc2-4f25-8c1e-9d3fdfb07bc9/IGVFFI3323DCKT.bam', GRCH38),
    ]
    for label, url, cs in cases:
        t0 = time.time()
        errs = validate_bigwig(url, cs)
        shown = errs if len(
            errs) <= 4 else errs[:4] + [f'... (+{len(errs)-4} more)']
        print(f'{label}\n   -> {shown}  ({time.time()-t0:.1f}s)\n')
