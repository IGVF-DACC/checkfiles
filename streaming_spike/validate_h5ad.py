"""Bucket 3 PoC: validate an h5ad by seeking over S3 with range requests (no download).

Mirrors `check_valid_h5ad_file_format` in src/checkfiles/checkfiles.py (requires the
anndata groups X, obs, var), but reads through an s3fs file object instead of a mounted
path. HDF5 is seekable-not-streamable: h5py jumps to scattered offsets, and s3fs's block
cache turns each seek+read into a bounded range request.

Returns a list of error strings ([] = valid).
"""
import h5py
import s3fs

REQUIRED_GROUPS = ['X', 'obs', 'var']
BLOCK_SIZE = 8 * 1024 * 1024


def validate_h5ad(s3_uri, anon=True, block_size=BLOCK_SIZE):
    """s3_uri: 's3://bucket/key'. anon=True for public buckets; False uses the
    default credential chain (Fargate task role)."""
    fs = s3fs.S3FileSystem(anon=anon, default_block_size=block_size)
    path = s3_uri[len('s3://'):] if s3_uri.startswith('s3://') else s3_uri
    try:
        with fs.open(path, 'rb', cache_type='blockcache', block_size=block_size) as fobj:
            with h5py.File(fobj, 'r') as f:
                missing = [g for g in REQUIRED_GROUPS if g not in f]
                if missing:
                    return ['Missing one or more required anndata groups X, obs and var. '
                            'This appears to be a generic h5 file.']
    except Exception as e:
        return [f'Exception checking h5ad file format: {e}']
    return []


if __name__ == '__main__':
    import time
    cases = [
        ('GOOD  h5ad 8.5MB IGVFFI2219RMEY',
         's3://igvf-public/2026/02/05/5b61f14f-e41c-460e-b94f-41afd2f07992/IGVFFI2219RMEY.h5ad'),
        ('BAD   generic .h5 (no X/obs/var) IGVFFI3698TJXH',
         's3://igvf-public/2025/08/14/2dd3264c-0da9-4b5b-8997-311336a31895/IGVFFI3698TJXH.h5'),
        ('BAD   tsv.gz posing as h5ad IGVFFI3093TLUQ',
         's3://igvf-public/2025/04/21/a46d5d2d-f325-401d-afe4-3139e3cd9765/IGVFFI3093TLUQ.tsv.gz'),
        ('GOOD  h5ad 656MB IGVFFI3805SQVR (size-independence check)',
         's3://igvf-public/2025/10/19/ff9fc59b-5b68-4387-b1d5-3872c6a9e8e6/IGVFFI3805SQVR.h5ad'),
    ]
    for label, uri in cases:
        t0 = time.time()
        errs = validate_h5ad(uri)
        print(f'{label}\n   -> {errs}  ({time.time()-t0:.1f}s)')
