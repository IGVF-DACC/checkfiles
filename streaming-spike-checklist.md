# S3-streaming feasibility spike — working checklist

**Scope:** Buckets 1–4a. Buckets 1–3 were closed first; Bucket 4a
(bed/bedpe/fastq/fasta/vcf/gvcf) was closed afterwards using a purpose-built docker image
that carries the four external binaries — see `streaming_spike/docker/`.

**Test data rule:** only released files from the IGVF portal (`api.data.igvf.org`).
Find by format: `https://api.data.igvf.org/search/?type=File&file_format={fmt}`.
The S3 location is the file object's `s3_uri` property (public bucket `igvf-public`).
Ask for help locating files rather than probing the portal API excessively.

**Feasibility bar per format:** (a) known-good real object → `[]`; (b) known-bad object rejected
with a sensible error; (c) data read by streaming/range requests, no mount and no whole-file
download; (d) where the checker itself changes (pyBigWig for big*, frictionless for tabular),
a side-by-side sanity check against the current checker's accept/reject boundary.

## Status legend
`[ ]` not started · `[x]` done · `[!]` deferred (needs data or tooling this pass could not get)

---

## 0. Environment
- [x] pip deps: `pyBigWig` (need `pyBigWig.remote == 1`), `frictionless[aws]`, `smart_open`, `boto3`, `h5py`, `s3fs`, `pyyaml`
- [x] conda-forge/bioconda `pysam` with libcurl + S3 plugins (micromamba) — gates Bucket 2
- [x] confirm network reach: pypi, `api.data.igvf.org`, `igvf-public.s3.us-west-2.amazonaws.com`
- [x] scratch dir for spike scripts: `$CLAUDE_JOB_DIR/tmp`

## 1. Bucket 2 — bam / cram (highest risk, do first)
- [x] pysam build actually opens `s3://` (not `Protocol not supported`)
- [x] locate a released bam on the portal
- [x] bam: `pysam.quickcheck` / `AlignmentFile` / `stats` against real object → good case
- [x] bam: known-bad case rejected (e.g. non-bam object)
- [!] locate a released cram + matching reference — **deferred, no such data exists** (local ref copies exist: `src/checkfiles/src/checkfiles/supporting_files/grch38.fa`, `grcm39.fa`)
- [!] cram: streaming open + `view→stats` pipe, good case
- [!] cram: known-bad case rejected

## 2. Bucket 3 — run the already-written functions vs real objects
- [x] bigWig — previously proven by the team; **re-confirmed independently here** (good → `[]`,
      wrong-assembly → 24 length mismatches, bam-as-bigWig → open error), up to 875 MB
- [!] bigBed — `validate_bigbed` written but never run — **deferred, no such data exists**
- [!] bigInteract — same function (opens as bigBed) — **deferred, no such data exists**
- [x] h5ad — written + run: h5py over s3fs file object (blockcache); reproduce `check_valid_h5ad_file_format` (X/obs/var present); good + bad

## 3. Bucket 1 — forward streaming
- [x] universal checks (md5, content-md5, size, gzip magic) — re-proven here as a **single** pass;
      md5 + content-md5 match portal values on a 52 MB .gz and a 10.3 GB bgzf bam
- [x] tabular txt/tsv — run vs real S3 objects, gzipped **and** plain, good + bad
- [x] seqspec — small YAML via smart_open → **`seqspec.utils.load_spec_stream`** → seqspec; no disk touched
      (`yaml.safe_load`, as the hand-off proposed, does **not** work — see run log)
- [x] large-object sanity: one Bucket 1 case on a big gzipped object — memory stays flat; record wall-clock + egress

## 4. Deliverable
- [x] one standalone PoC function per format above, each with recorded good/bad run output (in `streaming_spike/`)
- [x] update `streaming-migration-handoff.md` feasibility table with results
- [x] write up findings (incl. anything that did **not** work) — run log below + the
      "Spike findings added 2026-08-27" section appended to `streaming-migration-handoff.md`

---

## 5. Bucket 4a — FIFO into path-only external binaries
- [x] docker image carrying validateFiles, fastq_stats, FastaValidator, vcf_assembly_checker
- [x] bed — validateFiles via FIFO, good + bad
- [x] bedpe — validateFiles via FIFO, good + bad (supersedes the written-but-unrun wrapper)
- [x] fastq — validateFiles `-type=fastq` via FIFO, good + bad
- [x] fastq — fastq_stats via FIFO on RAW .gz bytes
- [x] fasta — FastaValidator via FIFO, good + bad
- [x] vcf — vcf_assembly_checker via FIFO + local reference, good + bad
- [x] gvcf — same code path as vcf (`vcf_sequence_check` does not branch on format)

---

## Out of scope
- Out of scope (deferred phase): dispatch refactor, `local_file_path` replacement, folding universal
  checks into one pass, pool wiring, crash-isolation, transient-vs-invalid retry, portal patching.

## Deliverables produced

| file | format(s) | mirrors |
|---|---|---|
| `streaming_spike/validate_universal.py` | all files | `File` in `src/checkfiles/file.py` |
| `streaming_spike/validate_tabular.py` | tsv / csv / txt | `tabular_file_check` |
| `streaming_spike/validate_seqspec.py` | seqspec yaml | `seqspec_file_check` |
| `streaming_spike/validate_bam.py` | bam | `bam_pysam_check` |
| `streaming_spike/validate_h5ad.py` | h5ad | `check_valid_h5ad_file_format` |
| `streaming_spike/validate_bigwig.py` | bigWig | replaces `validateFiles -type=bigWig` |
| `streaming_spike/validate_bucket4a.py` | bed / bedpe / fastq / fasta / vcf / gvcf | `validate_files_check`, `validate_files_fastq_check`, `fasta_check`, `vcf_sequence_check` |
| `streaming_spike/docker/Dockerfile.spike` | Bucket 4a image | native-aarch64 build of the four external binaries |
| `streaming_spike/docker/run_4a.sh` | runner | mounts the repo + reference genomes, runs the 4a proofs |
| `streaming_spike/compare_local_vs_stream.py` | harness | feasibility bar (d) |

`validate_bigbed` (bigBed / bigInteract) is **not** in this directory: it stays in the hand-off doc
as written-but-unrun code, because no object exists to run it against. See open questions.

## Run log

### Environment (aarch64!)
Sandbox is `linux-aarch64`. micromamba env `spike` (python 3.11) from conda-forge+bioconda:
`pysam 0.24.0` (htslib 1.23.1), `pyBigWig` (**`remote == 1`**), `h5py 3.16.0` (ros3 driver present),
then pip: `s3fs 2026.7.0`, `frictionless 5.19.0` + aws, `smart_open 8.0.1`, `seqspec`.
The env is throwaway. Rebuild:

```bash
# NOTE the arch: this sandbox is aarch64, not linux-64
curl -sL -o mm.tar.bz2 https://micro.mamba.pm/api/micromamba/linux-aarch64/latest
python3 -c "import tarfile; t=tarfile.open('mm.tar.bz2','r:bz2'); \
            t.extract(t.getmember('bin/micromamba'),'.',filter='data')"
chmod +x bin/micromamba
export MAMBA_ROOT_PREFIX=$PWD/mamba
./bin/micromamba create -y -n spike -c conda-forge -c bioconda \
    python=3.11 pysam pybigwig h5py s3fs boto3 pyyaml
./mamba/envs/spike/bin/pip install -U s3fs fsspec "frictionless[aws]" "smart_open[s3]"
# seqspec MUST be the tag checkfiles pins -- the PyPI release has no seqspec_check
./mamba/envs/spike/bin/pip install --force-reinstall \
    "git+https://github.com/IGVF-DACC/seqspec.git@v25-09-23"
```

Then run any PoC **from the repo root** (schema paths in `constants.py` are repo-relative):
`<env>/bin/python streaming_spike/validate_tabular.py`

Environment traps hit along the way, so nobody repeats them:
- micromamba's `linux-64` tarball extracts fine and then fails `Exec format error`. Use `linux-aarch64`.
- No `bzip2` binary in the sandbox, so `tar -xj` fails; extract with python's `tarfile` (`r:bz2`).
- System python is **3.14**, too new for pyBigWig/pysam/h5py wheels — hence conda, not pip.
- `py_fasta_validator` has no aarch64 wheel and does not build here. It is only needed to *import*
  `checkfiles`, so `compare_local_vs_stream.py` stubs `FastaValidator`. Nothing compared uses fasta.
- The **PyPI** `seqspec` has no `seqspec_check`; only the pinned `v25-09-23` tag does.

### Portal inventory (`file_format` facet, `type=File`, **all statuses**, 31530 files total)
yaml 15267 · bam 2851 · tar 2111 · bed 1946 · fastq 1759 · h5ad 1592 · hdf5 1497 · tbi 1439 ·
bai 1256 · tsv 644 · rds 543 · csv 199 · **bigWig 125** · vcf 56 · fasta 49 · pod5 47 · txt 18 ·
bedpe 2 · (others small)
Released-only counts run slightly lower (e.g. bam 2799, h5ad 1531, tsv 628, csv 195, bigWig 125);
the figures above are deliberately unfiltered, because that makes the absence below the stronger
claim: **no `bigBed`, no `bigInteract` and no `cram` exist on the portal in _any_ status.**
See open questions.

### Bucket 2 — bam: **PROVEN**
`pysam.AlignmentFile("s3://igvf-public/...bam")` opens on a **10 GB** object, reads 195 `@SQ`
records — no credentials needed (public bucket), no download. `https://` region-explicit URL works
identically. Full run (`streaming_spike/validate_bam.py`), replicating `bam_pysam_check`:
- GOOD IGVFFI3323DCKT (4.5 MB) → `[]`, `read_count=275576`, 2.8 s
- BAD tsv.gz as bam → `SamtoolsError ... was not identified as sequence data.`
- BAD bigWig as bam → `SamtoolsError ... could not be opened for reading.`
- BAD nonexistent key → `SamtoolsError ... could not be opened for reading.`

**Finding — cost:** `bam_pysam_check` makes ~3 full passes (`quickcheck`, `stats`,
`count(until_eof=True)`). Streaming works, but that is 3x full-object egress per bam. Worth
revisiting at integration time (e.g. derive the sorted flag + read count from one pass).

**Finding — transient vs invalid:** a *missing key* and a *corrupt file* produce the same
`could not be opened for reading` SamtoolsError. The later refactor cannot distinguish them from
the message alone; it needs a HEAD/existence probe or an errno, or it will patch network/404
failures back to the portal as content verdicts.

### Bucket 3 — h5ad: **PROVEN**
`streaming_spike/validate_h5ad.py`, h5py over an s3fs blockcache file object (8 MB blocks),
replicating `check_valid_h5ad_file_format`:
- GOOD IGVFFI2219RMEY (8.5 MB) → `[]`, 0.8 s
- BAD IGVFFI3698TJXH — real generic `.h5` "cell by gene and guide matrix", no X/obs/var →
  `Missing one or more required anndata groups X, obs and var...` (exactly the case the check exists for)
- BAD tsv.gz as h5ad → `Unable to synchronously open file (file signature not found)`
- GOOD IGVFFI3805SQVR (**656 MB**) → `[]` in **0.9 s** — same wall-clock as the 8 MB file, which is
  direct evidence only header/metadata ranges are fetched, not the object.

`anon=True` used for the public bucket; `anon=False` picks up the default credential chain
(Fargate task role) unchanged. `ros3` driver is present in the conda h5py but was not needed —
the s3fs file object is the portable path, as the handoff predicted.

### Bucket 1 — tabular (tsv/csv/txt): **PROVEN**
`streaming_spike/validate_tabular.py` — full port of `tabular_file_check`, returning the same
error dict. Two path-dependent pieces replaced by streaming: `get_header_row` now streams only
the leading lines with smart_open and stops at the first non-`#` line, and gzip detection reads
two bytes. frictionless gets the URL.
- GOOD IGVFFI7982RBWP tsv.gz, `guide RNA sequences` → `{}` (0.7 s) — exercises the schema path,
  `describe()` field inference, and `GuideRnaSequencesCheck`
- GOOD IGVFFI3093TLUQ tsv.gz, `SNP effect matrix` → `{}` — no-schema path (`skip_errors=['type-error']`)
- GOOD IGVFFI9219AECP **plain, non-gzipped** csv 6.7 MB → `{}` (2.6 s)
- BAD same tsv validated against the guide RNA schema → 158 errors, `missing-label` ×12,
  `incorrect-label` ×5, full production error dict
- BAD bam posing as tsv → `'utf-8' codec can't decode byte 0xb3 in position 4`

**Finding — anonymous access:** smart_open and frictionless both sign S3 requests through boto3,
so reading a *public* bucket with no credentials fails `NoCredentialsError`. smart_open takes an
unsigned client via `transport_params`; frictionless's `S3Loader` has **no unsigned option**, so
under `anon` the PoC rewrites `s3://` to the region-explicit https URL and its RemoteLoader serves
it with range requests. Not a production problem (the Fargate task role supplies credentials and
`s3://` works), but any local/CI testing against public objects hits it.

### Bucket 1 — seqspec: **PROVEN**
`streaming_spike/validate_seqspec.py` — port of `seqspec_file_check`. Object streamed into memory
(~1.5 KB) and handed to seqspec's own `load_spec_stream`.
- GOOD IGVFFI2649SJNI, IGVFFI3966CWRQ (onlist checks skipped) → `{}`
- BAD tsv.gz as seqspec → `found character '\t' that cannot start any token ... line 2, column 7`
- BAD bam as seqspec → `'utf-8' codec can't decode byte 0x8b in position 1`

**Correction to the hand-off doc:** it says `yaml.safe_load` → seqspec. That does not work — spec
YAML carries python object tags (`!Assay`, `!Region`) and seqspec loads with `yaml.Loader`. Use
`seqspec.utils.load_spec_stream`, which is the exact streaming twin of `load_spec` (which is only
`open(spec_fn)` + `load_spec_stream`). Zero disk touched.

**Finding — `spec_fn` is still a path, but harmlessly so.** `seqspec_check(spec, spec_fn,
filter_type)` uses `spec_fn` only as `os.path.dirname(spec_fn)`, and only for onlist/read entries
that carry a local path. IGVF specs reference portal http(s) URLs instead — confirmed with the team
that local ones never occur — so passing the object key is enough and nothing here needs a mount.
(The onlist-ON run reported one onlist "does not exist" — that is the unauthenticated portal HEAD
with no `IGVF_API_KEY`/`IGVF_SECRET_KEY`, not a streaming failure.)

### Bucket 3 — bigWig: **re-confirmed independently** (`streaming_spike/validate_bigwig.py`)
- GOOD IGVFFI4381NFYZ (30 MB, GRCh38) → `[]` 1.3 s
- GOOD IGVFFI3803JOCY (**502 MB**) → `[]` 1.7 s
- GOOD IGVFFI5621HHJK (**875 MB**, GRCm39 vs mm39.chrom.sizes) → `[]` **2.1 s**
- BAD GRCh38 bigWig vs mm39.chrom.sizes → 24 chrom length mismatches
- BAD bam posing as bigWig → `could not open as bigWig: Received an error during file opening!`
Wall-clock is flat from 30 MB to 875 MB: only header/index/probed intervals are fetched.

### Bucket 1 — universal checks (size, md5, content-md5, gzip magic): **PROVEN (incl. 10.3 GB)**
`streaming_spike/validate_universal.py` — one forward pass computes all four. (The local `File`
class in `src/checkfiles/file.py` reads the object *twice*: raw for md5, then through `gzip.open`
for content-md5, plus an `os.path.getsize`.)
- 52 MB txt.gz IGVFFI7082TATW → size OK, md5 `2a622d39...` **matches portal**,
  content_md5 `1a040eb7...` **matches the portal's own `content_md5sum`**. 2.1 s, peak RSS 65 MB
- 1.18 GB h5ad IGVFFI7941FRSD → size OK, md5 matches portal. 43.4 s, **peak RSS 65 MB — identical**

- **10.3 GB bam IGVFFI3397GPAJ** (bgzf, genuinely multi-member gzip) → size OK, md5
  `f9bb3847...` **matches portal**, content_md5 `0d1cb673...` **matches the portal's own
  `content_md5sum`**. 377 s, **peak RSS 64 MB**

Peak RSS is 64-65 MB across a **200x** size range (52 MB → 10.3 GB), confirming the hand-off's
flat-memory claim end to end. Throughput ~25-27 MB/s from this sandbox (not a Fargate-representative
number; a 10 GB object took 6.3 minutes here).

The 10 GB bgzf run is also the ground-truth check on the multi-member gzip fix below: matching the
portal's published `content_md5sum` on a real multi-member object is what proves it correct.

**Finding — multi-member gzip would have corrupted content-md5.** A single
`zlib.decompressobj` stops at the end of the *first* gzip member and parks the rest in
`unused_data`. bgzf (bam, tabix'd vcf) and any `cat a.gz b.gz` are multi-member, so a naive
streaming content-md5 silently hashes only the first member while `gzip.open` — what the current
code uses — spans all of them. The PoC now restarts the decompressor on each member boundary.
**Anyone writing the streaming version of this check must handle it or content_md5sum will
disagree with the mounted implementation on exactly the largest files.**

### Feasibility bar (d) — streamed vs the CURRENT local checker: **AGREES**
`streaming_spike/compare_local_vs_stream.py` downloads small objects purely to obtain a
local-path baseline, runs checkfiles' real unmodified `tabular_file_check` / `bam_pysam_check` /
`check_valid_h5ad_file_format` on them, and diffs against the streaming PoC on the same objects.

| case | local | stream | agree |
|---|---|---|---|
| tabular GOOD guide RNA sequences | valid | valid | yes |
| tabular GOOD no-schema SNP effect matrix | valid | valid | yes |
| tabular BAD wrong schema for content | INVALID | INVALID | yes |
| bam GOOD alignments | valid | valid | yes |
| bam BAD tsv.gz posing as bam | INVALID | INVALID | yes |
| h5ad GOOD anndata | valid | valid | yes |
| h5ad BAD generic .h5 | INVALID | INVALID | yes |

Accept/reject boundary matches on every case, and the **error payloads are byte-identical on 6 of
7**. The 7th differs only in the file path echoed inside the samtools message (local temp path vs
`s3://` URL) — no semantic drift.

Note: `py_fasta_validator` has no aarch64 wheel and fails to build here, so `FastaValidator` is
stubbed to let `checkfiles` import. Nothing compared touches fasta.

### Bucket 4a environment: the x86_64 problem (aarch64 host, 16 KB pages)
`docker/Dockerfile` is implicitly x86_64 — it installs a prebuilt `validateFiles` (UCSC ships
linux.x86_64 only) and `vcf_assembly_checker` (EBI ships linux x86_64 only). Neither can run
here, and **emulation is not an option**: this host has a **16 KB page size**, and qemu-user
cannot map x86_64 shared objects at that granularity. Any amd64 binary needing libstdc++ dies
with `libstdc++.so.6: failed to map segment from shared object` — confirmed for `apt-get`,
`validateFiles` and `vcf_assembly_checker`, with qemu 10.2.3 and binfmt correctly registered
(`mount -t binfmt_misc` + `tonistiigi/binfmt --install amd64`; simple binaries like `uname` do
run, so the emulator itself works). So all four tools were obtained natively for aarch64 in
`streaming_spike/docker/Dockerfile.spike`:

| tool | how |
|---|---|
| `validateFiles` | built from UCSC source, `jksrc.v442.zip` (2 patches, below) |
| `vcf_assembly_checker` | bioconda `vcf-validator` has a native linux-aarch64 build (0.10.2) |
| `fastq_stats` | Rust source; needs rustup — ubuntu's cargo 1.75 rejects the v4 `Cargo.lock` |
| `FastaValidator` | `py_fasta_validator` builds fine once `python3-dev` is present |

**Finding — validateFiles must come from `jksrc.vNNN.zip`, not a kent git clone.** kent's
`bamFile.c`/`knetUdc.c` call `cram_get_Md5`, `cram_get_ref_url`, `cram_get_cache_dir`,
`cram_set_cache_url`, `knet_init_alt`, and master additionally `cram_check_required_refs()`.
**None of these exist in any upstream htslib** (checked 1.20 / 1.21 / 1.22 / develop) — they are
UCSC's forked htslib, which ships vendored inside jksrc under `src/htslib`. Building against
stock htslib compiles and then fails at link with undefined references to exactly those symbols.
`v442` also matches the validateFiles version the repo pins.

Two source patches are still needed on aarch64 / modern distros:
1. `htmshell.c:714` compares a `va_list` against NULL. Fine on x86_64 (`va_list` is an array
   type that decays to a pointer), a hard error on aarch64 (it is a struct).
2. `jksql.c:1121-1122` uses `my_bool` and `MYSQL_OPT_SSL_VERIFY_SERVER_CERT`, both removed in
   MySQL 8 / MariaDB Connector-C 3.x. Neutralising that block only disables MySQL
   server-certificate verification, and this binary never opens a MySQL connection — checkfiles
   always passes `-chromInfo=<file>`, never `-chromDb`, so MySQL is link-time only.

Also note `libhts-dev` pulls `libcurl4-gnutls-dev`, which conflicts with `libcurl4-openssl-dev`.

## Deferred by decision: bigBed, bigInteract, cram

`api.data.igvf.org` holds **zero** files of these three formats in any status, so none of them
could be run against a real object. **Team decision (2026-08-28): leave them until such data
actually exists.** The reasoning, and what a future reader should pick up:

- **cram** is expected to behave like bam, which is proven. Two real differences to expect when the
  time comes: the checker needs a reference (`-T`, and local copies already sit in
  `src/checkfiles/src/checkfiles/supporting_files/{grch38,grcm39}.fa`), and `cram_pysam_check` uses
  a `samtools view -h -T ref | samtools stats -` pipe rather than a single call.
- **bigBed / bigInteract**: `validate_bigbed` is already written (in the hand-off doc) and should
  just need a run. **Do not reach for the bed FIFO pattern for these.** Despite the name they are
  not a bed variant at the transport level — they are indexed binary that seeks immediately, which
  is what killed `validateFiles -type=bigWig stdin` with `Illegal seek / lseek(0, -4, SEEK_END)`
  and emptied Bucket 4b. pyBigWig over range requests is the approach that works, the same one
  already proven for bigWig. `bigInteract` opens as a bigBed; the `SQL()` schema check against
  `src/schemas/as/interact.as` remains optional.

*(Also resolved: seqspec onlist/read entries never use a local path in practice — confirmed by the
team — so streaming's lack of a spec directory is a non-issue.)*

### Bucket 4a — bed / bedpe / fastq / fasta / vcf: **PROVEN**
`streaming_spike/validate_bucket4a.py`, run inside `checkfiles-spike:4a` via
`streaming_spike/docker/run_4a.sh`. A writer thread streams the object into a named FIFO
while the tool reads it as an ordinary path. Ports `validate_files_check`,
`validate_files_fastq_check`, `fasta_check` and `vcf_sequence_check`, returning the same
error dicts.

| case | result |
|---|---|
| GOOD bed (mpra_element, GRCh38) IGVFFI8982IPDD | `{}` 0.2 s |
| BAD fastq streamed as bed | `found 1 columns, expected 11` |
| GOOD bedpe (element to gene interactions) IGVFFI6067WOIM | `{}` 0.3 s |
| BAD bed streamed as bedpe | `found 11 columns, expected 10` |
| GOOD fastq via validateFiles IGVFFI2243EVBX | `{}` 0.2 s |
| BAD bed streamed as fastq | `sequence name first char invalid (got 'c', wanted '@')` |
| GOOD fastq via fastq_stats (RAW .gz) | `read_count: 13, mean_read_length: 50` |
| GOOD fasta IGVFFI2830EFZS | `{}` 0.2 s |
| BAD bed streamed as fasta | `the first line does not start with a > (rule 1 violated).` |
| GOOD vcf (GRCh38) IGVFFI4053BKXV | `{}` 0.3 s |
| BAD bed streamed as vcf | `Number of matches: 0/1` |
| BAD vcf vs wrong assembly (GRCm39) | `matches 3315/13909 (23.8%)`, `Contig 'chr20' not found` |

gvcf needs no separate proof: `vcf_sequence_check` does not branch on file_format, so it is
the same code path as vcf.

Compression behaves exactly as the hand-off warned: `validateFiles` on a FIFO does **not**
decompress (no `.gz` extension to key off), so the stream is decompressed upstream and fed as
plain text, while `fastq_stats` decompresses itself and gets the raw `.gz` bytes.

**Finding — open the FIFO before touching the network.** The obvious writer body
(`with s_open(url) as fin: with open(fifo,'wb') as out: copyfileobj(...)`) deadlocks whenever
the remote read raises: the writer dies before ever opening the write end, and the tool sits in
`open()` on the read end forever — a hang instead of an error. Open the FIFO **first**, then
read; the reader is then guaranteed to reach EOF, and the stream error is still reported.

**Finding — an in-process C extension cannot be fed by a writer thread.** FastaValidator is a
python C extension, not an external binary. It blocks while holding the GIL, so the writer
*thread* is never scheduled to open its end and the two deadlock — reproducibly, and only for
fasta, since the other three tools are subprocesses that release the GIL. Fixes tried:
- writer in a **fork**ed process — unreliable: forking after the earlier thread-based cases
  inherits lock state with no threads alive to release it; passed alone, hung in the full run.
- writer in a **spawn**ed process — child exited before opening the FIFO, same hang.
- **running the validator itself in a subprocess** — works, and restores the same shape as
  every other Bucket 4a tool. This is what the code does.
