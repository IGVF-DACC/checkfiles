"""Bucket 1 PoC: the universal checks (size, md5, content-md5, gzip magic) over a stream.

Reproduces what `File` in src/checkfiles/file.py computes from a mounted path, but from
a single forward pass over an S3 stream. The local class reads the file twice (once raw
for md5, once through gzip.open for content-md5) plus an os.path.getsize; here the raw
chunks feed the md5 hasher and a zlib decompressobj at the same time, so one pass over
the network yields all four values.

Purpose of the run: show that memory stays flat as object size grows, and record
wall-clock / egress for a large object.

This is a standalone PoC. Folding these checks into checkfiles' real dispatch is the
later refactor, not this spike.
"""
import hashlib
import resource
import sys
import time
import zlib

import boto3
from botocore import UNSIGNED
from botocore.config import Config
from smart_open import open as s_open

S3_REGION = 'us-west-2'
CHUNK = 1 << 16  # 64 KB, same order as shutil.copyfileobj


def _transport_params(url, anon):
    if anon and url.startswith('s3://'):
        return {'client': boto3.client('s3', config=Config(signature_version=UNSIGNED),
                                       region_name=S3_REGION)}
    return {}


def universal_checks(url, anon=False, chunk_size=CHUNK):
    """One forward pass. Returns dict with size, md5sum, is_gzipped, content_md5sum."""
    md5 = hashlib.md5()
    content_md5 = hashlib.md5()
    size = 0
    head = b''
    # wbits=47 -> auto-detect gzip/zlib header; only fed if the object is gzip
    decomp = zlib.decompressobj(47)
    is_gzipped = None
    content_md5_failed = None

    def feed(chunk):
        """Decompress across gzip MEMBER boundaries. A single decompressobj stops at the
        end of the first member and parks the rest in unused_data -- which would silently
        truncate the content md5 of any multi-member gzip stream (bgzf bam/vcf, or plain
        `cat a.gz b.gz`). gzip.open, which the local File class uses, spans members, so we
        must too or the streamed content_md5sum would disagree with the mounted one."""
        nonlocal decomp
        out = decomp.decompress(chunk)
        while decomp.eof and decomp.unused_data:
            tail = decomp.unused_data
            decomp = zlib.decompressobj(47)
            out += decomp.decompress(tail)
        return out

    with s_open(url, 'rb', compression='disable',
                transport_params=_transport_params(url, anon)) as fin:
        while chunk := fin.read(chunk_size):
            size += len(chunk)
            md5.update(chunk)
            if is_gzipped is None:
                head += chunk
                if len(head) >= 2:
                    is_gzipped = head[:2] == b'\x1f\x8b'
            if is_gzipped and content_md5_failed is None:
                try:
                    content_md5.update(feed(chunk))
                except zlib.error as e:
                    content_md5_failed = str(e)

    result = {
        'size': size,
        'md5sum': md5.hexdigest(),
        'is_gzipped': bool(is_gzipped),
    }
    if is_gzipped:
        result['content_md5sum'] = (None if content_md5_failed
                                    else content_md5.hexdigest())
        if content_md5_failed:
            result['content_md5_error'] = content_md5_failed
    return result


if __name__ == '__main__':
    cases = [
        ('txt.gz 52 MB IGVFFI7082TATW',
         's3://igvf-public/2026/07/18/2c5d2821-aa09-454a-904b-e71572422b5e/IGVFFI7082TATW.txt.gz',
         52375386, '2a622d394931f8834a8b0d764c12984f'),
        ('h5ad 1.18 GB IGVFFI7941FRSD',
         's3://igvf-public/2025/07/25/ff9c14d7-7821-4bc1-abb3-ec06e0c8ed0a/IGVFFI7941FRSD.h5ad',
         1184792688, None),
        ('bam 10.3 GB IGVFFI3397GPAJ (bgzf: gzip magic + content-md5 over 10 GB)',
         's3://igvf-public/2025/10/15/ffd43c22-72b7-4a95-96bc-ff351f085ee4/IGVFFI3397GPAJ.bam',
         10328851925, 'f9bb38470f6c8bbd398e6d7e4f4a6b66'),
    ]
    only = sys.argv[1:] or None
    for label, url, expect_size, expect_md5 in cases:
        if only and not any(o in label for o in only):
            continue
        t0 = time.time()
        r = universal_checks(url, anon=True)
        dt = time.time() - t0
        peak_mb = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024
        size_ok = 'OK' if r['size'] == expect_size else f"MISMATCH (portal {expect_size})"
        md5_ok = ('OK' if expect_md5 is None or r['md5sum'] == expect_md5
                  else f'MISMATCH (portal {expect_md5})')
        print(f'{label}\n'
              f'   size={r["size"]} [{size_ok}]  md5={r["md5sum"]} [vs portal: {md5_ok}]\n'
              f'   is_gzipped={r["is_gzipped"]}  content_md5={r.get("content_md5sum")}'
              f'{" err=" + r["content_md5_error"] if r.get("content_md5_error") else ""}\n'
              f'   {dt:.1f}s  ({r["size"]/dt/1e6:.0f} MB/s)  peak RSS {peak_mb:.0f} MB\n')
