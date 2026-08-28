"""Bucket 4a PoC: stream S3 objects into path-only external binaries via a named FIFO.

These tools accept only a file path and read sequentially, so they cannot take an
`s3://` URL and we do not want a full download. A named FIFO bridges the gap: a writer
thread streams the object into the FIFO while the tool reads it as an ordinary path.

Compression is per-tool and per-transport -- the single biggest trap here:
  * `validateFiles` on a FIFO does NOT decompress (it keys off the .gz extension, which a
    FIFO does not have), so we decompress in python and feed it plain text.
  * `fastq_stats` decompresses itself, so it gets the RAW .gz bytes.
  * Never name the FIFO *.gz to trigger extension-based decompression: some gzip readers
    seek to the last 4 bytes (ISIZE), which fails on a FIFO.

Each validator mirrors the corresponding function in src/checkfiles/checkfiles.py and
returns the same error dict shape ({} = valid).

Requires the external binaries; run inside the image built from
streaming_spike/docker/Dockerfile.spike.
"""
import os
import shutil
import subprocess
import sys
import tempfile
import threading

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..',
                                'src', 'checkfiles'))

import boto3
from botocore import UNSIGNED
from botocore.config import Config
from smart_open import open as s_open

S3_REGION = 'us-west-2'


def _transport_params(url, anon):
    if anon and url.startswith('s3://'):
        return {'client': boto3.client('s3', config=Config(signature_version=UNSIGNED),
                                       region_name=S3_REGION)}
    return {}


class FifoStream:
    """Streams a remote object into a named FIFO from a writer thread.

    decompress=True  -> smart_open infers .gz from the key and yields plain text bytes
    decompress=False -> raw bytes pass through untouched

    The reader must be a SUBPROCESS. Every tool here is one, which is why a writer
    thread suffices: the subprocess runs independently of the GIL. An in-process C
    extension reader (FastaValidator) would block holding the GIL and deadlock this
    thread -- see validate_fasta_stream for how that case is handled.
    """

    def __init__(self, url, decompress, anon=False, name='stream'):
        self.url = url
        self.decompress = decompress
        self.anon = anon
        self.name = name
        self.error = None
        self._tmpdir = None
        self._thread = None
        self.path = None

    def __enter__(self):
        self._tmpdir = tempfile.mkdtemp(prefix='fifo_')
        # deliberately NOT named *.gz -- see module docstring
        self.path = os.path.join(self._tmpdir, self.name)
        os.mkfifo(self.path)
        self._thread = threading.Thread(target=self._feed, daemon=True)
        self._thread.start()
        return self

    def _feed(self):
        compression = 'infer_from_extension' if self.decompress else 'disable'
        # Open the FIFO FIRST, before touching the network. If the remote read raises
        # (bad URL, credentials, network) and we have not yet opened the write end, a
        # reader blocked in open() on the other end waits forever -- the tool hangs
        # instead of failing. Opening first guarantees the reader always reaches EOF,
        # and the error is still reported via self.error.
        try:
            with open(self.path, 'wb') as out:   # blocks until the tool opens its end
                try:
                    with s_open(self.url, 'rb', compression=compression,
                                transport_params=_transport_params(self.url, self.anon)) as fin:
                        shutil.copyfileobj(fin, out)
                except BrokenPipeError:
                    # tool exited early (e.g. rejected the file) -- not a stream failure
                    pass
                except Exception as e:
                    self.error = f'{type(e).__name__}: {e}'
        except Exception as e:
            self.error = f'{type(e).__name__}: {e}'

    def __exit__(self, *exc):
        # drain the FIFO so a writer blocked on a tool that never read cannot hang us
        if self._thread.is_alive():
            try:
                with open(self.path, 'rb') as drain:
                    while drain.read(1 << 16):
                        pass
            except Exception:
                pass
        self._thread.join(timeout=60)
        try:
            os.remove(self.path)
            os.rmdir(self._tmpdir)
        except OSError:
            pass
        return False


def _run(cmd):
    """Run a tool, returning (returncode, combined output)."""
    p = subprocess.run(cmd, capture_output=True)
    out = (p.stdout + p.stderr).decode(errors='replace').rstrip('\n')
    return p.returncode, out


# --------------------------------------------------------------------------- #
# validateFiles-backed formats: bed, bedpe, fastq
# --------------------------------------------------------------------------- #

def get_validate_files_args(file_format, file_format_type, chrom_info_file,
                            content_type=None, schema=None):
    """Copied verbatim from checkfiles.get_validate_files_args. Copied rather than
    imported because importing checkfiles pulls in pysam/frictionless/seqspec/h5py,
    none of which belong in this Bucket 4a image."""
    from constants import VALIDATE_FILES_ARGS
    schema = VALIDATE_FILES_ARGS if schema is None else schema
    if file_format == 'bedpe' and content_type == 'element to gene interactions':
        args = list(schema[(file_format, content_type)])
    else:
        args = list(schema[(file_format, file_format_type)])
    args.append('chromInfo=' + chrom_info_file)
    return args


def validate_files_stream(url, file_format, file_format_type, assembly,
                          content_type=None, anon=False):
    """Streaming port of `validate_files_check`. validateFiles does NOT decompress a
    FIFO, so the stream is decompressed upstream and fed as plain text."""
    from constants import ASSEMBLY_TO_CHROMINFO_PATH_MAP

    error = {}
    if assembly not in ASSEMBLY_TO_CHROMINFO_PATH_MAP:
        return {'validate_files': f'assembly {assembly} is not supported. '
                                  f'Valid assemblies: {ASSEMBLY_TO_CHROMINFO_PATH_MAP.keys()}'}
    chrom_info_file_path = ASSEMBLY_TO_CHROMINFO_PATH_MAP[assembly]
    try:
        validate_args = get_validate_files_args(
            file_format, file_format_type, chrom_info_file_path, content_type)
    except KeyError:
        return {'validate_files': f'file_format: {file_format} '
                                  f'file_format_type: {file_format_type} combination not allowed.'}

    with FifoStream(url, decompress=True, anon=anon, name=file_format) as fifo:
        rc, out = _run(['validateFiles'] + validate_args + [fifo.path])
    if rc != 0:
        error['validate_files'] = out
    elif fifo.error:
        error['validate_files'] = f'stream error: {fifo.error}'
    return error


def validate_fastq_stream(url, anon=False):
    """Streaming port of `validate_files_fastq_check` (validateFiles -type=fastq)."""
    error = {}
    with FifoStream(url, decompress=True, anon=anon, name='fastq') as fifo:
        rc, out = _run(['validateFiles', '-type=fastq', fifo.path])
    if rc != 0:
        error['validate_files'] = out
    elif fifo.error:
        error['validate_files'] = f'stream error: {fifo.error}'
    return error


def fastq_stats_stream(url, anon=False):
    """fastq_stats over a FIFO. Unlike validateFiles this tool handles gzip itself, so
    it gets the RAW .gz bytes. It aggregates and emits only at EOF, so it cannot
    deadlock a serial writer."""
    error = {}
    with FifoStream(url, decompress=False, anon=anon, name='fastq_gz') as fifo:
        rc, out = _run(['fastq_stats', fifo.path])
    if rc != 0:
        error['fastq_stats'] = out
    elif fifo.error:
        error['fastq_stats'] = f'stream error: {fifo.error}'
    return error, (out if rc == 0 else None)


# --------------------------------------------------------------------------- #
# fasta -- FastaValidator (python C extension, path-only)
# --------------------------------------------------------------------------- #

def validate_fasta_stream(url, anon=False):
    """Streaming port of `fasta_check`. The original decompresses the whole file into a
    NamedTemporaryFile on disk; here the decompressed bytes go straight into a FIFO.

    FastaValidator is a python C EXTENSION, not an external binary, so calling it in
    process blocks the interpreter while holding the GIL -- the writer thread never gets
    scheduled to open its end of the FIFO and both sides deadlock. Running the validator
    in a subprocess restores the same shape as the other Bucket 4a tools: an external
    process reads the FIFO while this process streams into it.

    (A writer *process* instead of a writer thread was tried first and is not reliable
    here: fork inherits lock state from the earlier thread-based cases, and spawn
    re-imports the module in a fresh interpreter -- in both cases the child could exit
    before opening the FIFO, leaving the reader blocked in open() forever.)
    """
    from constants import FASTA_VALIDATION_INFO

    error = {}
    with FifoStream(url, decompress=True, anon=anon, name='fasta') as fifo:
        rc, out = _run([sys.executable, '-c',
                        'import sys; from FastaValidator import fasta_validator; '
                        'sys.exit(fasta_validator(sys.argv[1]))', fifo.path])
    if rc != 0:
        error['fasta_error'] = FASTA_VALIDATION_INFO.get(rc, f'unknown code {rc}: {out}')
    elif fifo.error:
        error['fasta_error'] = f'stream error: {fifo.error}'
    return error


# --------------------------------------------------------------------------- #
# vcf / gvcf -- vcf_assembly_checker (needs a local reference genome)
# --------------------------------------------------------------------------- #

def validate_vcf_stream(url, assembly, anon=False, assembly_report=None):
    """Streaming port of `vcf_sequence_check`. The reference genome stays a real local
    path (it is randomly accessed via its .fai); only the VCF is streamed."""
    from constants import (ASSEMBLY_FOR_VCF, ASSEMBLY_TO_SEQUENCE_FILE_MAP,
                           ASSEMBLY_REPORT_FILE_PATH)

    error = {}
    if assembly not in ASSEMBLY_FOR_VCF:
        return {'vcf_error': f'assembly {assembly} is not supported.'}
    ref_file_path = ASSEMBLY_TO_SEQUENCE_FILE_MAP[assembly]
    if assembly_report is None:
        assembly_report = ASSEMBLY_REPORT_FILE_PATH[assembly]

    with FifoStream(url, decompress=True, anon=anon, name='vcf') as fifo:
        cmd = ['vcf_assembly_checker', '-i', fifo.path, '-f', ref_file_path]
        if assembly_report and os.path.exists(assembly_report):
            cmd += ['-a', assembly_report]
        rc, out = _run(cmd)
    if rc != 0:
        error['vcf_error'] = out
    elif fifo.error:
        error['vcf_error'] = f'stream error: {fifo.error}'
    return error


if __name__ == '__main__':
    import json as _json
    import time

    BED_GOOD = ('s3://igvf-public/2026/06/24/bf228884-3a07-472d-aafe-128775b57abe/'
                'IGVFFI8982IPDD.bed.gz')
    BEDPE_GOOD = ('s3://igvf-public/2026/05/07/ed62fe08-32d0-4dc6-babc-1ec84a9eadd1/'
                  'IGVFFI6067WOIM.bedpe.gz')
    FASTQ_GOOD = ('s3://igvf-public/2024/02/12/6f774580-b4da-4591-8a4b-20df4917c928/'
                  'IGVFFI2243EVBX.fastq.gz')
    FASTA_GOOD = ('s3://igvf-public/2025/05/12/12ff0dcc-f4d8-457a-b761-a428946637ba/'
                  'IGVFFI2830EFZS.fasta.gz')
    VCF_GOOD = ('s3://igvf-public/2026/07/13/8a7eb415-bc25-466f-b6ee-b4c6560ecbe8/'
                'IGVFFI4053BKXV.vcf.gz')

    only = sys.argv[1:] or None

    def show(label, fn):
        if only and not any(o.lower() in label.lower() for o in only):
            return
        t0 = time.time()
        try:
            r = fn()
        except Exception as e:
            r = {'UNCAUGHT': f'{type(e).__name__}: {e}'}
        txt = _json.dumps(r, default=str)
        print(f'{label}\n   -> {txt[:400]}{"..." if len(txt) > 400 else ""}  '
              f'({time.time()-t0:.1f}s)\n')

    show('GOOD  bed (mpra_element, GRCh38) IGVFFI8982IPDD',
         lambda: validate_files_stream(BED_GOOD, 'bed', 'mpra_element', 'GRCh38',
                                       'reporter genomic element effects', anon=True))
    show('BAD   fastq streamed as bed',
         lambda: validate_files_stream(FASTQ_GOOD, 'bed', 'mpra_element', 'GRCh38',
                                       'reporter genomic element effects', anon=True))
    show('GOOD  bedpe (element to gene interactions) IGVFFI6067WOIM',
         lambda: validate_files_stream(BEDPE_GOOD, 'bedpe', None, 'GRCh38',
                                       'element to gene interactions', anon=True))
    show('BAD   bed streamed as bedpe',
         lambda: validate_files_stream(BED_GOOD, 'bedpe', None, 'GRCh38',
                                       'element to gene interactions', anon=True))
    show('GOOD  fastq via validateFiles IGVFFI2243EVBX',
         lambda: validate_fastq_stream(FASTQ_GOOD, anon=True))
    show('BAD   bed streamed as fastq',
         lambda: validate_fastq_stream(BED_GOOD, anon=True))
    show('GOOD  fastq via fastq_stats (RAW .gz bytes) IGVFFI2243EVBX',
         lambda: fastq_stats_stream(FASTQ_GOOD, anon=True))
    show('GOOD  fasta IGVFFI2830EFZS',
         lambda: validate_fasta_stream(FASTA_GOOD, anon=True))
    show('BAD   bed streamed as fasta',
         lambda: validate_fasta_stream(BED_GOOD, anon=True))
    show('GOOD  vcf (GRCh38) IGVFFI4053BKXV',
         lambda: validate_vcf_stream(VCF_GOOD, 'GRCh38', anon=True))
    show('BAD   bed streamed as vcf',
         lambda: validate_vcf_stream(BED_GOOD, 'GRCh38', anon=True))
    show('BAD   vcf checked against the wrong assembly (GRCm39)',
         lambda: validate_vcf_stream(VCF_GOOD, 'GRCm39', anon=True))
    show('BAD   unsupported assembly',
         lambda: validate_vcf_stream(VCF_GOOD, 'hg19', anon=True))
