# S3-streaming spike — start here

**Question:** can every checkfiles format be validated by streaming from S3 — no goofys/FUSE
mount, no full download — so the suite can move to Fargate?

**Answer: yes.** Every format that has data on the portal is proven. bigBed, bigInteract and cram
are deferred: the portal holds zero files of them in any status, so there is nothing to run against.

Nothing in `src/checkfiles/` was changed. This is a spike: standalone PoCs only.

## What to read

| | |
|---|---|
| this file | orientation + what was proven against which object |
| `streaming-spike-checklist.md` | full run log, findings, how to rebuild the environments |
| `streaming-migration-handoff.md` | original hand-off, updated in place (bucket model, per-format table) |
| `streaming_spike/` | the PoC code |

## What was proven, and against what

Each PoC mirrors the corresponding function in `src/checkfiles/checkfiles.py` and returns the same
error shape. Every "bad" case reuses a real portal object of the *wrong* format (plus wrong-assembly
cases for bigWig and vcf), so both good and bad paths ran against real data.

| file_format | how we validated | s3_uri of the file(s) used |
|---|---|---|
| all formats (size, md5, content-md5, gzip magic) | one forward stream through the hashers (`smart_open`); md5 **and** content-md5 matched the portal's own values | `s3://igvf-public/2026/07/18/2c5d2821-aa09-454a-904b-e71572422b5e/IGVFFI7082TATW.txt.gz` (52 MB)<br>`s3://igvf-public/2025/07/25/ff9c14d7-7821-4bc1-abb3-ec06e0c8ed0a/IGVFFI7941FRSD.h5ad` (1.18 GB)<br>`s3://igvf-public/2025/10/15/ffd43c22-72b7-4a95-96bc-ff351f085ee4/IGVFFI3397GPAJ.bam` (10.3 GB) |
| tsv / csv / txt | frictionless over the object; header-row detection and gzip sniff also streamed | `s3://igvf-public/2025/03/21/b1d6bab7-8f09-4640-b5bd-580f0b0d20fc/IGVFFI7982RBWP.tsv.gz` (schema path)<br>`s3://igvf-public/2025/04/21/a46d5d2d-f325-401d-afe4-3139e3cd9765/IGVFFI3093TLUQ.tsv.gz` (no-schema path)<br>`s3://igvf-public/2023/10/11/e07d6688-2792-496a-9b01-9cd510f2ce75/IGVFFI9219AECP.csv` (plain, non-gz) |
| yaml (seqspec) | streamed into memory, `seqspec.utils.load_spec_stream` — no disk | `s3://igvf-public/2026/06/04/fffb3779-1583-4dd6-bf09-53392e1cbf24/IGVFFI2649SJNI.yaml.gz`<br>`s3://igvf-public/2025/09/09/fff3c6c2-0fee-455c-854c-e76d6c650a30/IGVFFI3966CWRQ.yaml.gz` |
| bam | pysam opens `s3://` directly (htslib range requests), no credentials needed | `s3://igvf-public/2026/06/10/155918fc-8dc2-4f25-8c1e-9d3fdfb07bc9/IGVFFI3323DCKT.bam`<br>`s3://igvf-public/2025/10/15/ffd43c22-72b7-4a95-96bc-ff351f085ee4/IGVFFI3397GPAJ.bam` (10 GB, header read) |
| h5ad | h5py over an s3fs blockcache file object; 656 MB validated in 0.9 s (metadata ranges only) | `s3://igvf-public/2026/02/05/5b61f14f-e41c-460e-b94f-41afd2f07992/IGVFFI2219RMEY.h5ad`<br>`s3://igvf-public/2025/10/19/ff9fc59b-5b68-4387-b1d5-3872c6a9e8e6/IGVFFI3805SQVR.h5ad` (656 MB)<br>bad: `s3://igvf-public/2025/08/14/2dd3264c-0da9-4b5b-8997-311336a31895/IGVFFI3698TJXH.h5` (real generic `.h5`) |
| bigWig | pyBigWig over https range requests, **replacing** `validateFiles`; 875 MB in 2.1 s | `s3://igvf-public/2026/05/07/fac6e773-ae1c-487a-ae9d-c5af72c91046/IGVFFI4381NFYZ.bigWig`<br>`s3://igvf-public/2026/05/07/fd04d5c7-947a-4c3a-8dfd-2257d1c0554e/IGVFFI3803JOCY.bigWig` (502 MB)<br>`s3://igvf-public/2025/10/11/fd306b94-a7c5-4e68-8cf4-42336b3568a2/IGVFFI5621HHJK.bigWig` (875 MB, GRCm39) |
| bed | `validateFiles` fed by a named FIFO (decompressed upstream) | `s3://igvf-public/2026/06/24/bf228884-3a07-472d-aafe-128775b57abe/IGVFFI8982IPDD.bed.gz` |
| bedpe | `validateFiles` via FIFO | `s3://igvf-public/2026/05/07/ed62fe08-32d0-4dc6-babc-1ec84a9eadd1/IGVFFI6067WOIM.bedpe.gz` |
| fastq | `validateFiles -type=fastq` via FIFO (plain text) **and** `fastq_stats` via FIFO (raw `.gz`) | `s3://igvf-public/2024/02/12/6f774580-b4da-4591-8a4b-20df4917c928/IGVFFI2243EVBX.fastq.gz` |
| fasta | `FastaValidator` via FIFO, validator run in a subprocess | `s3://igvf-public/2025/05/12/12ff0dcc-f4d8-457a-b761-a428946637ba/IGVFFI2830EFZS.fasta.gz` |
| vcf | `vcf_assembly_checker` via FIFO + local reference genome | `s3://igvf-public/2026/07/13/8a7eb415-bc25-466f-b6ee-b4c6560ecbe8/IGVFFI4053BKXV.vcf.gz` |
| gvcf | same code path as vcf — `vcf_sequence_check` does not branch on file_format | covered by the vcf run |
| bigBed / bigInteract | pyBigWig (function written, never run) | **none exist on the portal — deferred** |
| cram | pysam + reference; expected to follow bam | **none exist on the portal — deferred** |

## Does the streamed verdict match today's checker?

`streaming_spike/compare_local_vs_stream.py` runs checkfiles' real, unmodified
`tabular_file_check` / `bam_pysam_check` / `check_valid_h5ad_file_format` against downloaded copies
and diffs them against the streamed verdicts. **Accept/reject agrees on all 7 cases; the error
payloads are byte-identical on 6 of 7** (the 7th differs only in the file path echoed inside a
samtools message).

## The five findings that matter for the refactor

1. **Multi-member gzip breaks a naive streaming content-md5.** `zlib.decompressobj` stops after the
   first gzip member; bgzf (bam, tabix'd vcf) is multi-member, while `gzip.open` — what `file.py`
   uses today — spans members. Get this wrong and content_md5sum silently disagrees with the mounted
   implementation on exactly the largest files. Verified correct against the portal's published
   `content_md5sum` for a 10.3 GB bgzf bam.
2. **Open the FIFO before the network read.** Open the object first and a failed read kills the
   writer before it opens the write end — the tool then blocks in `open()` forever. A transient S3
   error becomes a hang instead of an error.
3. **A path-only tool that is an in-process C extension cannot be fed by a writer thread.**
   FastaValidator blocks holding the GIL. Run the validator in a subprocess (writer processes,
   forked or spawned, do not fix it).
4. **bam costs ~3 full passes** (`quickcheck` → `stats` → `count(until_eof=True)`) = 3x egress per
   bam. Worth collapsing when this is integrated.
5. **A missing S3 key and a corrupt file raise the same SamtoolsError**, so transient-vs-invalid
   cannot be decided from the message text — it needs an existence/HEAD probe or an errno.

## Reproducing

Buckets 1–3 need a conda env (pysam/pyBigWig with libcurl); Bucket 4a needs the docker image that
carries `validateFiles`, `fastq_stats`, `FastaValidator` and `vcf_assembly_checker`:

```bash
docker build -f streaming_spike/docker/Dockerfile.spike -t checkfiles-spike:4a .
./streaming_spike/docker/run_4a.sh
```

Both recipes, and the environment traps behind them, are in `streaming-spike-checklist.md`.
Note that `docker/Dockerfile` is implicitly x86_64 (prebuilt `validateFiles` and
`vcf_assembly_checker`); `Dockerfile.spike` builds those natively so the proofs could run on an
arm64 host. That is a sandbox concern only — Fargate is x86_64.
