"""Bucket 1 PoC: validate a tabular file (tsv/csv/txt) streamed from S3.

Faithful port of `tabular_file_check` in src/checkfiles/checkfiles.py, with the two
path-dependent pieces replaced by streaming equivalents:

  * `get_header_row` no longer opens a local path -- it streams only the leading lines
    of the object with smart_open and stops at the first non-comment line.
  * frictionless is handed the `s3://` URL, which routes through its S3Loader
    (a seekable range-request stream over boto3, default credential chain).

Gzip detection also streams: two bytes, not a whole file.
Returns the same error dict shape as the original ({} = valid).

Run from the repo root -- TABULAR_FILE_SCHEMAS paths are repo-relative.
"""
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src', 'checkfiles'))

import boto3
from botocore import UNSIGNED
from botocore.config import Config
from frictionless import system, validate, describe, Schema, Dialect
from frictionless.exception import FrictionlessException
from smart_open import open as s_open

from constants import (
    TABULAR_FILE_SCHEMAS, NO_HEADER_CONTENT_TYPE, UTF_8_ENCODING,
    MAX_NUM_ERROR_FOR_TABULAR_FILE, MAX_NUM_DETAILED_ERROR_FOR_TABULAR_FILE,
)
from guide_rna_sequences_check import GuideRnaSequencesCheck


S3_REGION = 'us-west-2'


def s3_to_https(url, region=S3_REGION):
    """s3://BUCKET/KEY -> region-explicit https. The global BUCKET.s3.amazonaws.com form
    can 301, so always pin the region."""
    if not url.startswith('s3://'):
        return url
    bucket, _, key = url[len('s3://'):].partition('/')
    return f'https://{bucket}.s3.{region}.amazonaws.com/{key}'


def _transport_params(url, anon):
    """smart_open signs s3:// requests with boto3, so anonymous access to a public
    bucket needs an explicitly unsigned client. In production (Fargate task role)
    anon=False and the default credential chain applies."""
    if anon and url.startswith('s3://'):
        return {'client': boto3.client('s3', config=Config(signature_version=UNSIGNED),
                                       region_name=S3_REGION)}
    return {}


def is_gzipped_remote(url, anon=False):
    """Gzip magic from the first two bytes -- one small ranged read, no download."""
    with s_open(url, 'rb', compression='disable',
                transport_params=_transport_params(url, anon)) as f:
        return f.read(2) == b'\x1f\x8b'


def get_header_row_remote(url, is_gzipped, encoding=UTF_8_ENCODING, anon=False):
    """Streaming port of get_header_row: count leading '#' lines, stop at the first
    non-comment line. Reads only the head of the object, never the whole file."""
    compression = '.gz' if is_gzipped else 'disable'
    count = 0
    with s_open(url, 'rt', encoding=encoding, compression=compression,
                transport_params=_transport_params(url, anon)) as f:
        for line in f:
            if line.lstrip().startswith('#'):
                count += 1
            else:
                break
    return count + 1


def validate_tabular(file_format, content_type, url, is_gzipped=None,
                     schemas=TABULAR_FILE_SCHEMAS, max_error=MAX_NUM_ERROR_FOR_TABULAR_FILE,
                     allow_additional_fields=True, schema_path=None, anon=False):
    """anon=True reads a public bucket without credentials (spike only). frictionless's
    S3Loader has no unsigned option, so under anon the s3:// URL is rewritten to its
    region-explicit https form, which its RemoteLoader serves with range requests.
    In production anon=False and s3:// goes through S3Loader on the task role."""
    try:
        system.trusted = True
        error = {}
        if is_gzipped is None:
            is_gzipped = is_gzipped_remote(url, anon=anon)

        frictionless_url = s3_to_https(url) if anon else url

        if content_type not in NO_HEADER_CONTENT_TYPE:
            header_row = get_header_row_remote(url, is_gzipped, anon=anon)
            dialect = Dialect(comment_char='#', header_rows=[header_row])
        else:
            dialect = Dialect(header=False, comment_char='#')

        frictionless_options = {
            'dialect': dialect,
            'format': file_format,
            'encoding': UTF_8_ENCODING,
        }
        if is_gzipped:
            frictionless_options['compression'] = 'gz'

        if not schema_path:
            schema_path = schemas.get(content_type)
        if not schema_path:
            report = validate(frictionless_url, limit_errors=max_error,
                              skip_errors=['type-error'], **frictionless_options)
        else:
            checks = []
            if content_type == 'barcode to sample mapping':
                infer_schema = describe(frictionless_url, type='schema', **frictionless_options)
                if len(infer_schema.fields) not in [6, 3]:
                    return {'tabular_file_error':
                            f'barcode to sample mapping file should have 6 or 3 columns, '
                            f'but found {len(infer_schema.fields)} columns'}
                schema_path = schema_path[0] if len(infer_schema.fields) == 6 else schema_path[1]
                report = validate(frictionless_url, schema=schema_path, limit_errors=max_error,
                                  checks=checks, **frictionless_options)
            else:
                if content_type in ['guide RNA sequences', 'prime editing guide RNA sequences']:
                    checks = [GuideRnaSequencesCheck()]
                if not allow_additional_fields:
                    report = validate(frictionless_url, schema=schema_path, limit_errors=max_error,
                                      checks=checks, **frictionless_options)
                else:
                    infer_schema = describe(frictionless_url, type='schema', **frictionless_options)
                    schema = Schema.from_descriptor(schema_path)
                    if len(infer_schema.fields) > len(schema.fields):
                        for i in range(len(schema.fields), len(infer_schema.fields)):
                            schema.add_field(infer_schema.fields[i])
                    report = validate(frictionless_url, schema=schema, limit_errors=max_error,
                                      checks=checks, **frictionless_options)
    except (UnicodeDecodeError, FrictionlessException) as e:
        return {'tabular_file_error': f'exception occurred when checking tabular file: {e}'}

    if not report.valid:
        flat = report.flatten(['rowNumber', 'fieldNumber', 'type', 'note', 'description'])
        tabular_file_error = {
            'schema': schema_path,
            'error_number_limit': max_error,
            'number_of_errors': len(flat),
        }
        for row in flat:
            error_type = row[2]
            if error_type in tabular_file_error:
                tabular_file_error[error_type]['count'] += 1
                if len(tabular_file_error[error_type]['details']) < MAX_NUM_DETAILED_ERROR_FOR_TABULAR_FILE:
                    tabular_file_error[error_type]['details'].append(
                        {'row_number': row[0], 'field_number': row[1], 'note': row[3]})
            else:
                tabular_file_error[error_type] = {
                    'count': 1,
                    'description': row[4],
                    'details': [{'row_number': row[0], 'field_number': row[1], 'note': row[3]}],
                }
        tabular_file_error['error_types'] = list(set(row[2] for row in flat))
        error = {'tabular_file_error': tabular_file_error}
    return error


if __name__ == '__main__':
    import time, json as _json
    cases = [
        ('GOOD  tsv.gz guide RNA sequences (schema + GuideRnaSequencesCheck) IGVFFI7982RBWP',
         'tsv', 'guide RNA sequences',
         's3://igvf-public/2025/03/21/b1d6bab7-8f09-4640-b5bd-580f0b0d20fc/IGVFFI7982RBWP.tsv.gz'),
        ('GOOD  tsv.gz no-schema path (SNP effect matrix) IGVFFI3093TLUQ',
         'tsv', 'SNP effect matrix',
         's3://igvf-public/2025/04/21/a46d5d2d-f325-401d-afe4-3139e3cd9765/IGVFFI3093TLUQ.tsv.gz'),
        ('GOOD  plain (non-gz) csv 6.7MB IGVFFI9219AECP',
         'csv', 'linkage disequilibrium',
         's3://igvf-public/2023/10/11/e07d6688-2792-496a-9b01-9cd510f2ce75/IGVFFI9219AECP.csv'),
        ('BAD   SNP effect matrix validated against the guide RNA sequences schema',
         'tsv', 'guide RNA sequences',
         's3://igvf-public/2025/04/21/a46d5d2d-f325-401d-afe4-3139e3cd9765/IGVFFI3093TLUQ.tsv.gz'),
        ('BAD   bam posing as tsv IGVFFI3323DCKT',
         'tsv', 'SNP effect matrix',
         's3://igvf-public/2026/06/10/155918fc-8dc2-4f25-8c1e-9d3fdfb07bc9/IGVFFI3323DCKT.bam'),
    ]
    for label, fmt, ct, url in cases:
        t0 = time.time()
        try:
            err = validate_tabular(fmt, ct, url, anon=True)
        except Exception as e:
            err = {'UNCAUGHT': f'{type(e).__name__}: {e}'}
        s = _json.dumps(err, default=str)
        print(f'{label}\n   -> {s[:600]}{"..." if len(s) > 600 else ""}  ({time.time()-t0:.1f}s)\n')
