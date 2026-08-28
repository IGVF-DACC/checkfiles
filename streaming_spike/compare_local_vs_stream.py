"""Feasibility bar (d): does the streamed checker agree with the CURRENT local checker?

Downloads a few small objects to a temp dir, runs checkfiles' real, unmodified
`tabular_file_check` / `bam_pysam_check` / `check_valid_h5ad_file_format` against the local
copy, runs the streaming PoC against the S3 URL, and diffs the verdicts.

The download here exists only to obtain the local-path baseline to compare against -- it is
not part of the streaming path being proven.

FastaValidator (py_fasta_validator) has no aarch64 wheel and does not build in this sandbox,
so it is stubbed purely to let `checkfiles` import. Nothing compared here touches fasta.
"""
import os
import sys
import types
import tempfile
import json

REPO = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..')
sys.path.insert(0, os.path.join(REPO, 'src', 'checkfiles'))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

_stub = types.ModuleType('FastaValidator')
_stub.fasta_validator = lambda *a, **k: 0
sys.modules.setdefault('FastaValidator', _stub)

import boto3
from botocore import UNSIGNED
from botocore.config import Config

import checkfiles
from validate_tabular import validate_tabular
from validate_bam import validate_bam
from validate_h5ad import validate_h5ad

S3 = boto3.client('s3', config=Config(signature_version=UNSIGNED), region_name='us-west-2')


def fetch(s3_uri, dest_dir):
    bucket, _, key = s3_uri[len('s3://'):].partition('/')
    dest = os.path.join(dest_dir, os.path.basename(key))
    S3.download_file(bucket, key, dest)
    return dest


def norm(x):
    return json.dumps(x, sort_keys=True, default=str)


def main():
    tmp = tempfile.mkdtemp(prefix='spike_baseline_')
    results = []

    # --- tabular: good (schema path) and bad (wrong schema for the content) ---
    tsv_guide = 's3://igvf-public/2025/03/21/b1d6bab7-8f09-4640-b5bd-580f0b0d20fc/IGVFFI7982RBWP.tsv.gz'
    tsv_snp = 's3://igvf-public/2025/04/21/a46d5d2d-f325-401d-afe4-3139e3cd9765/IGVFFI3093TLUQ.tsv.gz'
    for uri, ct, label in [
        (tsv_guide, 'guide RNA sequences', 'tabular GOOD guide RNA sequences'),
        (tsv_snp, 'SNP effect matrix', 'tabular GOOD no-schema SNP effect matrix'),
        (tsv_snp, 'guide RNA sequences', 'tabular BAD  wrong schema for content'),
    ]:
        local = fetch(uri, tmp)
        local_res = checkfiles.tabular_file_check('tsv', ct, local, is_gzipped=True)
        stream_res = validate_tabular('tsv', ct, uri, anon=True)
        results.append((label, local_res, stream_res))

    # --- bam: good, and a non-bam object ---
    bam = 's3://igvf-public/2026/06/10/155918fc-8dc2-4f25-8c1e-9d3fdfb07bc9/IGVFFI3323DCKT.bam'
    local = fetch(bam, tmp)
    local_res = checkfiles.bam_pysam_check(local, 'alignments')
    stream_errs, stream_info = validate_bam(bam, 'alignments')
    stream_res = {'bam_error': stream_errs[0]} if stream_errs else stream_info
    results.append(('bam GOOD alignments', local_res, stream_res))

    local = fetch(tsv_snp, tmp)
    local_res = checkfiles.bam_pysam_check(local, 'alignments')
    stream_errs, stream_info = validate_bam(tsv_snp, 'alignments')
    stream_res = {'bam_error': stream_errs[0]} if stream_errs else stream_info
    results.append(('bam BAD  tsv.gz posing as bam', local_res, stream_res))

    # --- h5ad: good, and a generic .h5 with no X/obs/var ---
    h5ad = 's3://igvf-public/2026/02/05/5b61f14f-e41c-460e-b94f-41afd2f07992/IGVFFI2219RMEY.h5ad'
    h5 = 's3://igvf-public/2025/08/14/2dd3264c-0da9-4b5b-8997-311336a31895/IGVFFI3698TJXH.h5'
    for uri, label in [(h5ad, 'h5ad GOOD anndata'), (h5, 'h5ad BAD  generic .h5')]:
        local = fetch(uri, tmp)
        local_res = checkfiles.check_valid_h5ad_file_format(local)
        stream_errs = validate_h5ad(uri, anon=True)
        stream_res = {'h5ad_error': stream_errs[0]} if stream_errs else {}
        results.append((label, local_res, stream_res))

    print(f'{"case":42} {"local verdict":14} {"stream verdict":14} agree?')
    print('-' * 92)
    all_agree = True
    for label, loc, strm in results:
        loc_v = 'INVALID' if (loc and any(k.endswith('_error') or k in ('bam_error',)
                                          for k in loc)) else 'valid'
        strm_v = 'INVALID' if (strm and any(k.endswith('_error') for k in strm)) else 'valid'
        agree = loc_v == strm_v
        all_agree &= agree
        print(f'{label:42} {loc_v:14} {strm_v:14} {"YES" if agree else "*** NO ***"}')
    print('-' * 92)
    print('accept/reject boundary matches on every case' if all_agree
          else 'DIVERGENCE -- see detail below')

    print('\n--- detail (local vs stream payload) ---')
    for label, loc, strm in results:
        same = norm(loc) == norm(strm)
        print(f'\n{label}   payload identical: {same}')
        if not same:
            print(f'   local : {norm(loc)[:300]}')
            print(f'   stream: {norm(strm)[:300]}')


if __name__ == '__main__':
    main()
