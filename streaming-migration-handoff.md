# checkfiles S3-streaming — feasibility spike hand-off

## Where we are: feasibility, not refactoring (read this first)

**This is a feasibility spike. We are NOT refactoring the suite yet.** The single goal of the current phase is to **prove that every required file format can be validated while streaming from S3** (HTTP range requests / streaming), with no goofys/FUSE mount and no full download.

Concretely, the deliverable of this phase is **one standalone proof-of-concept validation function per file format**, each demonstrated against real S3 objects to (a) return "valid" for a known-good file and (b) reject a known-bad file — reading the data by streaming, not from a mounted path or a local download.

**Out of scope right now** (do not start these yet):

- Refactoring `checkfiles.py`, the dispatch, or `get_file_validation_record_from_metadata`.
- Replacing the `local_file_path` abstraction, or building any handle/adapter layer.
- Folding the universal checks into a single pass, wiring into the `multiprocessing.Pool`, crash-isolation, retry/transient-error handling, or portal patching.

Those are the *next* project, and notes for them are preserved at the end under "Deferred until after feasibility is proven" so nothing is lost — but they are explicitly not this phase's work. The bar for "done" now is: **for each format, we have run a streaming validation against a real object and confirmed it behaves correctly.**

## The longer-term motivation (context only — not this phase's work)

The reason we're proving streaming feasibility is an eventual migration of `checkfiles` (`IGVF-DACC/checkfiles`, `dev` branch) from EC2 to **AWS Fargate**, validating objects of arbitrary size (including bigWig/bigBed files that can exceed 200 GB) without a mount and without a full download. The current suite funnels every validator through a single `local_file_path` backed by a goofys FUSE mount, and that approach cannot move to Fargate — which is *why* we need to establish, format by format, that a streaming alternative exists before committing to any rewrite.

## Why streaming (and not a mount or a download)

Two constraints of the eventual Fargate target are what make plain streaming the thing to prove, rather than assuming we can keep a path-based approach:

- **FUSE is unavailable on Fargate.** goofys, mountpoint-s3, and s3fs-fuse all require `/dev/fuse` and `CAP_SYS_ADMIN`/privileged mode, none of which Fargate grants. (EFS *is* mountable on Fargate, but it is not S3 — copying to EFS is just a download with extra steps.) So the current goofys-mount approach cannot be lifted as-is.
- **Downloading doesn't scale.** Fargate ephemeral storage caps at 200 GB, and we have bigWig files larger than that. Even under the cap, a full download per file is slow and adds egress + time cost.

Hence the spike: for each format, find an access mode that reads from S3 directly (range requests / streaming) with bounded memory and no whole-file download, and confirm the format's validator actually works through it. Formats differ in what they need, which is the bucket model below.

## The mental model: 4 buckets

Every file type sorts into one of four access strategies. For the spike, the bucket tells you which streaming approach to prove out for that format. (It will also be the natural framework for the eventual refactor, but that's later.)

**Bucket 1 — Forward streaming, we own the reader (single pass, no download).**
Data is read once, front to back, by our own Python. Stream the object (e.g. `smart_open`) through the check. Applies to: the universal checks (md5, content-md5, size, gzip-magic), tabular (txt/tsv), seqspec.

**Bucket 2 — htslib-native remote.** pysam/htslib can open an `s3://` URL directly and do its own range requests. We just hand it the URL. Applies to: bam, cram.

**Bucket 3 — Seekable remote random access via a library.** The format needs random access (seeks), but a Python library satisfies that with range requests against a seekable remote object — no download. Applies to: h5ad (h5py over s3fs/ros3), bigWig, bigBed, bigInteract (pyBigWig).

**Bucket 4a — External path-only binary, sequential.** A closed external binary that only accepts a file path, but reads sequentially. Feed it a **named FIFO** that a writer thread streams into. No download, no seeking. Applies to: fastq, fasta, bed, bedpe, vcf, gvcf.

**Bucket 4b — External path-only binary, random access.** A closed external binary that only accepts a path *and* seeks within the file. A FIFO/stream cannot satisfy this (it dies on `lseek`). This bucket is now **EMPTY** — bigWig/bigBed/bigInteract were the only members and were shown to be validatable via pyBigWig (Bucket 3) instead. This is the key feasibility result so far: the one format group that looked like it *required* a >200 GB download turned out not to.

## Per-format feasibility status

"Feasibility" here means: a standalone streaming validation has been demonstrated against a real object. The column tracks how far each format is toward that bar — not toward integration (which is out of scope now).

| File type | Bucket | Streaming approach to prove | Feasibility status |
|---|---|---|---|
| all files (md5, content-md5, size, gzip-magic) | 1 | stream the object through the hashers/size/magic | **Proven** — single-pass PoC; md5 + content-md5 match portal values; flat RSS 64-65 MB from 52 MB to **10.3 GB** |
| tabular (txt/tsv) | 1 | frictionless v5, `s3://` scheme or presigned https | **Proven** — real objects, gz + plain, schema + no-schema paths; payload identical to local checker |
| seqspec | 1 | read small YAML into memory via smart_open; **`seqspec.utils.load_spec_stream`** (NOT `yaml.safe_load`) | **Proven** — real objects, no disk touched |
| bam | 2 | pysam `quickcheck`/`stats`/`AlignmentFile` on `s3://` | **Proven** — conda-forge pysam 0.24.0 opens `s3://` anonymously on a 10 GB object; verdict identical to local checker |
| cram | 2 | pysam on `s3://` + reference file; keep `view→stats` pipe | **Blocked — no cram files exist on the portal** (see checklist open questions) |
| h5ad | 3 | h5py over s3fs file object (blockcache) or ros3 driver | **Proven** — 656 MB validates in 0.9 s (metadata ranges only); verdict identical to local checker |
| bigWig | 3 | pyBigWig: isBigWig + chroms vs chrom.sizes + start/end `stats()` probes | **Proven** — re-confirmed independently; 875 MB bigWig validates in 2.1 s |
| bigBed | 3 | pyBigWig: isBigBed + chroms vs chrom.sizes + start/end `entries()` probes | **Blocked — no bigBed files exist on the portal** (see checklist open questions) |
| bigInteract | 3 | pyBigWig (opens as bigBed); optional `SQL()` schema check vs `.as` | **Blocked — no bigInteract files exist on the portal** (see checklist open questions) |
| bed | 4a | validateFiles via FIFO | Not written (pattern established by bedpe) |
| bedpe | 4a | validateFiles via FIFO, **decompress to plain text** | **Shell path proven** (`Error count 0`); Python FIFO wrapper written, not run |
| fastq | 4a | validateFiles `-type=fastq` + fastq_stats via FIFO | Not written (stdin streaming explored earlier in-depth) |
| fasta | 4a | FastaValidator via FIFO (decompress upstream, not temp) | Not written |
| vcf | 4a | vcf_assembly_checker via FIFO + reference file | Not written |
| gvcf | 4a | vcf_assembly_checker via FIFO + reference file | Not written |

> **Spike run, 2026-08-27.** Buckets 1–3 closed against real released portal objects; working
> code in `streaming_spike/`, full run log and open questions in `streaming-spike-checklist.md`.
> Bucket 4a was out of scope for that pass (external binaries unavailable in the sandbox), and
> bigBed / bigInteract / cram are blocked on test data — **the portal holds zero files of those
> three formats in any status**, not merely zero released ones.

## Hard-won technical findings (don't rediscover these)

**Streaming memory is flat regardless of file size.** `shutil.copyfileobj(fin, dst)` moves one ~64 KB chunk at a time; OS pipe backpressure blocks the writer when the reader is slow, so the whole chain runs in lockstep at bounded memory. A 300 GB object streams in the same footprint as a 4 MB one. "Blocks for a long time" = throughput (synchronous, lots of bytes), **not** a deadlock.

**Deadlock risk is about the child's OUTPUT, not the input size.** A subprocess that emits large output *while* reading stdin can fill its stdout pipe buffer, stop reading, and deadlock a serial writer. Aggregators that emit only at EOF (e.g. `fastq_stats`) can't deadlock. When output volume could scale with input, feed stdin from a **thread** while `communicate()` drains stdout.

**`communicate()` closes stdin itself.** Do **not** manually `proc.stdin.close()` and then call `communicate()` — it flushes an already-closed pipe and raises `ValueError: flush of closed file`. Either let `communicate()` close it, or close it yourself and use `wait()` + read the pipes.

**Compression handling is per-tool and per-transport — this bites.** Whether to decompress upstream depends entirely on whether the downstream tool detects gzip itself, and stdin/FIFO strips the filename extension the tool may have relied on:
- `fastq_stats` handles gzip itself → pass **raw** `.gz` bytes (`smart_open(..., compression='disable')`).
- `validateFiles` on stdin/FIFO does **not** decompress (no `.gz` extension visible) → **decompress upstream** and feed plain text. (This exact issue produced a misleading `found 1 columns, expected 10` error on a bedpe file — validateFiles was parsing raw gzip bytes.)
- Do **not** name a FIFO `*.gz` to trigger extension-based decompression: some gzip readers seek to the last 4 bytes (ISIZE), which dies on a FIFO. Decompress in Python; keep the FIFO strictly plain-text and sequential.

**HDF5/h5ad is seekable, not streamable.** Even checking that groups `X`/`obs`/`var` exist requires seeking to scattered offsets. A pipe/FIFO fails on the first `seek()`. Use a seekable remote object: h5py accepts a file-like object, and s3fs (with block caching) or the `ros3` driver satisfies the seeks with range requests. Note: `ros3` is not in PyPI wheels — needs conda-forge/source build. s3fs file-object is the portable default.

**bigWig/bigBed/bigInteract killed the FIFO approach — hence pyBigWig.** `validateFiles -type=bigWig stdin` dies with `Illegal seek / lseek(0, -4, SEEK_END) failed`: it's an indexed binary format and seeks immediately. A FIFO fails identically. **pyBigWig** reads these over `https://` with libcurl range requests (header + index + only the intervals touched), so memory/egress stay bounded with no download. This is what empties Bucket 4b.

**pyBigWig can hard-abort the process (critical for pool safety).** On a corrupt/truncated file, or when the server doesn't return a size, the underlying libBigWig can kill the process rather than raise. The synchronous `validate_bigwig`/`validate_bigbed` functions are fine for **feasibility eval**, but **before they run inside the `multiprocessing.Pool` workers they must be isolated in a short-lived child process**, interpreting a negative `exitcode` (killed by signal) as "invalid file." Otherwise one bad file takes down a worker.

**pysam `s3://` support is build-dependent — CONFIRMED WORKING.** conda-forge/bioconda
`pysam 0.24.0` (htslib 1.23.1, linux-aarch64) opens `s3://igvf-public/...` with **no credentials
configured**, on a 10 GB object, and the region-explicit `https://` form behaves identically.
Original note retained below.

**pysam `s3://` support is build-dependent.** htslib reads `s3://`/`https://` natively *only if built with libcurl + S3 plugins*. conda-forge/bioconda pysam has it; some pip wheels throw `Protocol not supported`. Pin pysam from conda-forge in the image and add a **startup assertion** that opens a known S3 object so a bad build fails loudly, not mid-batch. Watch the egress gotcha: unbounded `fetch()` range requests can egress the whole tail — fine for our full-file reads (quickcheck/stats/count), but don't "optimize" into open-ended region fetches.

**frictionless v5 has a native S3 loader.** Passing an `s3://` URL routes through `S3Loader`, which wraps the object in a seekable range-request stream (`S3ByteStream`) over boto3 using the default credential chain (Fargate task role). `comment_char="#"` skips leading comment lines (replaces the manual `get_header_row` logic). `.gz` is auto-decompressed from the key extension. **Gotcha:** base `frictionless` does not include boto3 — the `s3://` scheme needs `frictionless[aws]` (or boto3) in the image, or it fails at read time.

**(Integration-time, not spike) Transient vs content-invalid must be distinguished.** At batch scale, S3 blips / throttles / expired presigned URLs will happen. A network failure must become a **retry**, not a permanent "invalid file" verdict patched back to the portal. Noted here so it isn't forgotten, but this belongs to the later refactor, not the feasibility spike — during the spike a raised/caught error is simply an informative result.

**(Integration-time, not spike) References ship in the image.** cram/vcf/gvcf need reference genomes; eventually bake them into the container image (or stage once at task start), never fetch per-file. For the spike, just point the checker at a local reference copy to prove the streaming input path works.

## URL mapping (s3:// → https)

`s3://BUCKET/KEY` → `https://BUCKET.s3.REGION.amazonaws.com/KEY`. Use the **region-explicit** endpoint (igvf buckets are `us-west-2`): the global `BUCKET.s3.amazonaws.com` form can return a 301 redirect that libcurl won't always follow. For private objects, generate a **presigned https URL** via boto3 (`generate_presigned_url`), which pyBigWig/frictionless-remote both accept.

## Working code so far

These are the standalone proof-of-concept functions produced so far. They are exactly the right shape for the spike: each takes an S3/https reference and returns a **list of error strings (`[]` = valid)**. They are deliberately **not** integrated into `checkfiles.py` — that's the later phase. (The pyBigWig ones are synchronous; the child-process isolation noted in the findings is an integration concern, not needed to prove feasibility.)

> **As of the 2026-08-27 run, the runnable code lives in `streaming_spike/`** — see the table in
> `streaming-spike-checklist.md`. Those versions are faithful ports of the *actual* checkfiles
> functions (same error-dict shapes, same constants and schemas) and supersede the sketches below,
> which are kept for context. The one exception is `validate_bigbed` below: it is still
> written-but-unrun, because no bigBed or bigInteract object exists to run it against.

### bigWig (proven; also in `streaming_spike/validate_bigwig.py`)

```python
import pyBigWig

def validate_bigwig(url, chrom_sizes_path):
    """Validate a remote bigWig via range requests. Returns list of errors ([] = valid)."""
    errors = []
    if not getattr(pyBigWig, "remote", 0):
        return ["pyBigWig not built with libcurl (pyBigWig.remote == 0)"]

    chrom_sizes = {}
    with open(chrom_sizes_path) as f:
        for line in f:
            if line.strip():
                name, length = line.split()[:2]
                chrom_sizes[name] = int(length)

    try:
        bw = pyBigWig.open(url)
    except (RuntimeError, OSError) as e:               # network flake vs bad file: see findings
        return [f"could not open as bigWig: {e}"]
    if bw is None:
        return ["open() returned None (not found / unreadable)"]
    try:
        if not bw.isBigWig():
            errors.append("not a bigWig")
        if (bw.header() or {}).get("nBasesCovered", 0) <= 0:
            errors.append("header reports zero bases covered")
        chroms = bw.chroms() or {}
        if not chroms:
            errors.append("no chromosomes")
        for c, length in chroms.items():
            if c not in chrom_sizes:
                errors.append(f"chrom {c} not in chrom.sizes")
            elif length != chrom_sizes[c]:
                errors.append(f"chrom {c} length {length} != {chrom_sizes[c]}")
        # exercise index + last data blocks at start AND end of the biggest chroms
        for name, length in sorted(chroms.items(), key=lambda kv: kv[1], reverse=True)[:3]:
            for lo, hi in [(0, min(10_000, length)), (max(0, length - 10_000), length)]:
                if hi > lo:
                    try:
                        bw.stats(name, lo, hi, type="mean", nBins=1)
                    except Exception as e:
                        errors.append(f"read failed {name}:{lo}-{hi}: {e}")
    finally:
        bw.close()
    return errors
```

### bigBed / bigInteract (written, **still not tested — no such file exists on the portal**)

```python
import pyBigWig

def validate_bigbed(url, chrom_sizes_path):
    """Validate a remote bigBed / bigInteract (bigInteract opens as bigBed)."""
    errors = []
    if not getattr(pyBigWig, "remote", 0):
        return ["pyBigWig not built with libcurl (pyBigWig.remote == 0)"]

    chrom_sizes = {}
    with open(chrom_sizes_path) as f:
        for line in f:
            if line.strip():
                name, length = line.split()[:2]
                chrom_sizes[name] = int(length)

    try:
        bb = pyBigWig.open(url)
    except (RuntimeError, OSError) as e:
        return [f"could not open as bigBed: {e}"]
    if bb is None:
        return ["open() returned None (not found / unreadable)"]
    try:
        if not bb.isBigBed():
            errors.append("not a bigBed")
        if (bb.header() or {}).get("nBasesCovered", 0) <= 0:
            errors.append("header reports zero bases covered")
        chroms = bb.chroms() or {}
        if not chroms:
            errors.append("no chromosomes")
        for c, length in chroms.items():
            if c not in chrom_sizes:
                errors.append(f"chrom {c} not in chrom.sizes")
            elif length != chrom_sizes[c]:
                errors.append(f"chrom {c} length {length} != {chrom_sizes[c]}")
        # entries() is the bigBed analog of stats(); wider window since features are sparse.
        # An empty result is NOT an error (no features in range); only an exception is.
        for name, length in sorted(chroms.items(), key=lambda kv: kv[1], reverse=True)[:3]:
            for lo, hi in [(0, min(1_000_000, length)), (max(0, length - 1_000_000), length)]:
                if hi > lo:
                    try:
                        bb.entries(name, lo, hi)
                    except Exception as e:
                        errors.append(f"read failed {name}:{lo}-{hi}: {e}")
    finally:
        bb.close()
    return errors
```

### tabular txt/tsv — *superseded by `streaming_spike/validate_tabular.py`*, which ports the real `tabular_file_check` (schemas, header-row detection, GuideRnaSequencesCheck)

```python
from frictionless import Resource, Dialect

def validate_tabular(source, fmt="tsv", comment_char="#", max_errors=100):
    """Validate a tabular file streamed from S3.
    source: 's3://bucket/key.tsv[.gz]' (boto3 task-role creds; needs frictionless[aws])
            or a presigned https URL. Auto-decompresses .gz by extension.
    Returns list of error strings ([] = valid)."""
    resource = Resource(source, format=fmt, dialect=Dialect(comment_char=comment_char))
    try:
        report = resource.validate()
    except Exception as e:
        return [f"could not read/validate tabular file: {e}"]
    if report.valid:
        return []
    errors = []
    for task in report.tasks:
        for err in task.errors:
            errors.append(f"{err.type}: {err.message}")
            if len(errors) >= max_errors:
                return errors + ["... (truncated)"]
    return errors
```

### bedpe via FIFO (shell path verified `Error count 0`; Python wrapper written, not run)

```python
import os, shutil, subprocess, tempfile, threading
from smart_open import open as s_open

def validate_bedpe(url, as_path, chrom_sizes_path, bed_type="bed3+7"):
    """Stream a (possibly gzipped) bedpe from S3 through validateFiles via a FIFO."""
    tmpdir = tempfile.mkdtemp()
    fifo = os.path.join(tmpdir, "bedpe")
    os.mkfifo(fifo)

    writer_error = {}
    def feed():
        try:
            with s_open(url, "rb") as fin:          # infer_from_extension -> decompresses .gz
                with open(fifo, "wb") as out:        # blocks until validateFiles opens read end
                    shutil.copyfileobj(fin, out)
        except Exception as e:
            writer_error["err"] = str(e)

    writer = threading.Thread(target=feed)
    writer.start()
    try:
        cmd = ["validateFiles", "-tab", f"-type={bed_type}",
               f"-as={as_path}", f"-chromInfo={chrom_sizes_path}", fifo]
        proc = subprocess.run(cmd, capture_output=True, text=True)
    finally:
        writer.join()
        os.remove(fifo)
        os.rmdir(tmpdir)

    if proc.returncode != 0:
        return [proc.stdout.strip() or proc.stderr.strip() or "validateFiles failed"]
    if writer_error:
        return [f"stream error: {writer_error['err']}"]
    return []
```

## Next steps for the spike (prioritized)

*Rewritten 2026-08-27 after the Buckets 1–3 run. Items 1, 2 (partly), 4, 5 and 6 of the original
list are done; what remains is below. Original ordering rationale — prove bam/cram first because
`s3://` support is build-dependent — was followed, and the pysam risk is now retired.*

**Blocked on test data (cannot proceed without help):**

1. **bigBed and bigInteract.** `validate_bigbed` is written but has never touched a real object,
   because `api.data.igvf.org` holds **zero** files of either format, while both are required per
   the README and `VALIDATE_FILES_ARGS`. Need a staging/sandbox portal, a specific `igvf-public`
   key, or a file from the team. Once an object exists this is a single run.
2. **cram.** Same situation — no released cram files on the portal, so Bucket 2 is only half
   proven. The pysam `s3://` risk is retired by the bam result, so cram should be quick: point
   `-T` at the local reference copies already in
   `src/checkfiles/src/checkfiles/supporting_files/{grch38,grcm39}.fa`.

**Blocked on tooling:**

3. **Bucket 4a (fastq, fasta, bed, bedpe, vcf, gvcf).** Out of scope for the 2026-08-27 run:
   `validateFiles`, `fastq_stats`, `FastaValidator` and `vcf_assembly_checker` were not available
   in that sandbox and are not pip-installable. Needs an environment carrying those binaries —
   the repo's docker image is the obvious source. The bedpe FIFO pattern is already written and
   its shell path proven, so the remaining wrappers follow it; mind the per-tool compression rule
   (decompress upstream for `validateFiles`, raw `.gz` bytes for `fastq_stats`).

**Open question, no blocker:**

4. **Does `urltype: local` occur in real IGVF seqspecs?** Such onlist/read entries resolve against
   the spec's directory, which streaming does not have. If they exist in practice, that path needs
   a plan before the refactor.

## Feasibility bar for each format (how to know a format is "proven")

For each format, "proven" means all of: (a) a known-good real object returns valid/`[]`; (b) a known-bad object is rejected with a sensible error; (c) the data was read by streaming from S3 (no mount, no whole-file download); (d) for the formats where we're changing the *checker* (pyBigWig replacing validateFiles for big*; frictionless for tabular), a quick side-by-side against the current checker on a few known-good and known-bad files shows they agree on the accept/reject boundary. Point (d) is the one place semantics can drift — where the old checker catches something the new one misses and it matters, note it (e.g. pyBigWig `SQL()` schema comparison for bigInteract, or a frictionless `Schema` for tabular) so the eventual refactor can decide whether to add it.

## Deferred until after feasibility is proven (NOT this phase)

Captured so the reasoning isn't lost — do not start these during the spike:

- **Dispatch refactor.** Replace `local_file_path` in `get_file_validation_record_from_metadata` with a handle abstraction exposing `.url()` (Bucket 2/3-https), `.stream()` (Bucket 1 + h5py-via-s3fs + frictionless), `.fifo()` (Bucket 4a), and `.local_path()` (download-to-ephemeral fallback only), so dispatch branches change only what they're handed.
- **Fold the universal checks into one pass** (size + md5 + content-md5 + gzip-magic from a single streamed read) so we don't re-read the object per check.
- **Production crash-isolation** for the pyBigWig validators: child process, interpret negative `exitcode` as invalid.
- **Transient-vs-invalid handling**: retry/backoff on read failures; never patch a network error back as a content verdict.
- **References in the image** for cram/vcf/gvcf, and the **pysam startup assertion** against a known S3 object.
- **Possible promotion of vcf/gvcf to Bucket 2** by rewriting on `pysam.VariantFile(s3url)` instead of the external `vcf_assembly_checker`.

## Repo / environment notes

- Repo: `IGVF-DACC/checkfiles`, `CHECK-281-test-streaming-forall` branch, `src/checkfiles/checkfiles.py`.
- AutoSql schemas: `src/schemas/as/`. Chrom sizes: `src/schemas/genome_builds/chrom_sizes/` (e.g. `GRCh38.chrom.sizes`, `mm39.chrom.sizes`).
- External binaries: UCSC `validateFiles`, `fastq_stats`, `FastaValidator` (py_fasta_validator), `vcf_assembly_checker`.
- Packages to have available for the spike: `pyBigWig` (libcurl-enabled — check `pyBigWig.remote == 1`), `frictionless[aws]` (pulls boto3; the base install does **not**), `smart_open`, `h5py` + `s3fs`, and a `pysam` build with libcurl S3 support (conda-forge/bioconda). Plus local copies of any reference genomes needed by the cram/vcf checkers.
- Test objects used so far (public, `--no-sign-request`): bigWig, bigInteract/bedpe, and fastq objects under `s3://igvf-public/...`. Use region-explicit https URLs for pyBigWig (e.g. `https://igvf-public.s3.us-west-2.amazonaws.com/...`).
- The `dev` branch README enumerates the required formats; the spike is done when every one of them has a proven streaming validation per the bar above.


## Spike findings added 2026-08-27 (Buckets 1–3)

**Multi-member gzip breaks a naive streaming content-md5.** A single `zlib.decompressobj` stops at
the end of the *first* gzip member and parks the remainder in `unused_data`. bgzf (bam, tabix'd
vcf) and any `cat a.gz b.gz` are multi-member, whereas `gzip.open` — what `File._calculate_content_md5sum`
uses today — spans members. A streaming content-md5 must restart the decompressor at each member
boundary or it will silently disagree with the mounted implementation, on exactly the biggest files.

**seqspec: use `load_spec_stream`, not `yaml.safe_load`.** The spec YAML carries python object tags
(`!Assay`, `!Region`); `safe_load` rejects them. `seqspec.utils.load_spec` is literally
`open(spec_fn)` + `load_spec_stream`, so the streaming swap is exact. Caveat: `seqspec_check(spec,
spec_fn, ...)` still takes a path and uses `os.path.dirname(spec_fn)` to resolve onlist/read entries
whose `urltype` is `local` — those have no meaning without a mount directory.

**Anonymous S3 is awkward for smart_open and frictionless (test-time only).** Both sign via boto3,
so reading a public bucket with no credentials raises `NoCredentialsError`. smart_open accepts an
unsigned client through `transport_params`; frictionless's `S3Loader` has **no unsigned option** —
fall back to the region-explicit https URL, which its RemoteLoader serves with range requests. Not
a production issue (task role), but it will bite anyone testing locally against `igvf-public`.

**bam costs ~3 full passes.** `bam_pysam_check` runs `quickcheck`, then `stats`, then
`count(until_eof=True)` — three full reads of the object. Streaming handles it at flat memory, but
that is 3x egress per bam; worth collapsing at integration time.

**A missing S3 key and a corrupt file produce the same SamtoolsError.** Both surface as
`could not be opened for reading`. The transient-vs-invalid split noted elsewhere in this document
cannot be made from the message text alone — it needs an existence/HEAD probe or an errno.
