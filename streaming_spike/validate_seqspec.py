"""Bucket 1 PoC: validate a seqspec YAML streamed from S3 into memory (no disk).

Port of `seqspec_file_check` in src/checkfiles/checkfiles.py. seqspec files are tiny
(~1.5 KB), so the object is streamed straight into memory and handed to seqspec's own
`load_spec_stream` -- the streaming counterpart of `load_spec`, which only wraps
`open(spec_fn)`.

NOTE: use seqspec's loader, not `yaml.safe_load`. The spec YAML carries python object
tags (`!Assay`, `!Region`, ...) and safe_load rejects them.

`seqspec_check(spec, spec_fn, ...)` takes a path, but only uses `os.path.dirname(spec_fn)`
to resolve onlist/read entries carrying a local path. IGVF specs reference portal http(s)
URLs and never use local ones, so a placeholder path is sufficient.

Returns the same error dict shape as the original ({} = valid).
"""
from constants import SEQSPEC_FILE_VERSION
from seqspec.seqspec_check import seqspec_check
from seqspec.seqspec_version import seqspec_version
from seqspec.utils import load_spec_stream
from smart_open import open as s_open
from botocore.config import Config
from botocore import UNSIGNED
import boto3
import io
import os
import sys

sys.path.insert(0, os.path.join(
    os.path.dirname(__file__), '..', 'src', 'checkfiles'))


S3_REGION = 'us-west-2'


def _transport_params(url, anon):
    if anon and url.startswith('s3://'):
        return {'client': boto3.client('s3', config=Config(signature_version=UNSIGNED),
                                       region_name=S3_REGION)}
    return {}


def validate_seqspec(url, validate_onlist_files=True, anon=False, spec_fn=None):
    """url: 's3://bucket/key.yaml[.gz]'. spec_fn is only used by seqspec to resolve
    local onlist/read paths, which IGVF specs do not use; it defaults to the object's own
    key so relative resolution keeps the same shape it had on the mount."""
    error = {}
    if 'IGVF_API_KEY' not in os.environ or 'IGVF_SECRET_KEY' not in os.environ:
        print('  [warn] IGVF_API_KEY / IGVF_SECRET_KEY not set: seqspec check cannot '
              'access files that are not released.', file=sys.stderr)
    if spec_fn is None:
        spec_fn = url[len('s3://'):] if url.startswith('s3://') else url
    try:
        with s_open(url, 'rt', encoding='utf-8',
                    transport_params=_transport_params(url, anon)) as fin:
            spec = load_spec_stream(io.StringIO(fin.read()))
        version = seqspec_version(spec)['file_version']
        if version != SEQSPEC_FILE_VERSION:
            return {'seqspec_error': f'The seqspec file version is {version}, '
                                     f'while version {SEQSPEC_FILE_VERSION} is required.'}
        filter_type = 'igvf' if validate_onlist_files else 'igvf_onlist_skip'
        errors = seqspec_check(spec, spec_fn, filter_type)
        if errors:
            error['seqspec_error'] = errors
    except Exception as e:
        error['seqspec_error'] = str(e)
    return error


if __name__ == '__main__':
    import time
    import json as _json
    cases = [
        ('GOOD  seqspec yaml.gz IGVFFI2649SJNI (onlist checks ON)',
         's3://igvf-public/2026/06/04/fffb3779-1583-4dd6-bf09-53392e1cbf24/IGVFFI2649SJNI.yaml.gz', True),
        ('GOOD  seqspec yaml.gz IGVFFI2649SJNI (onlist checks SKIPPED)',
         's3://igvf-public/2026/06/04/fffb3779-1583-4dd6-bf09-53392e1cbf24/IGVFFI2649SJNI.yaml.gz', False),
        ('GOOD  seqspec yaml.gz IGVFFI3966CWRQ',
         's3://igvf-public/2025/09/09/fff3c6c2-0fee-455c-854c-e76d6c650a30/IGVFFI3966CWRQ.yaml.gz', False),
        ('BAD   tsv.gz posing as seqspec IGVFFI3093TLUQ',
         's3://igvf-public/2025/04/21/a46d5d2d-f325-401d-afe4-3139e3cd9765/IGVFFI3093TLUQ.tsv.gz', False),
        ('BAD   bam posing as seqspec IGVFFI3323DCKT',
         's3://igvf-public/2026/06/10/155918fc-8dc2-4f25-8c1e-9d3fdfb07bc9/IGVFFI3323DCKT.bam', False),
    ]
    for label, url, onlist in cases:
        t0 = time.time()
        err = validate_seqspec(url, validate_onlist_files=onlist, anon=True)
        s = _json.dumps(err, default=str)
        print(
            f'{label}\n   -> {s[:500]}{"..." if len(s) > 500 else ""}  ({time.time()-t0:.1f}s)\n')
