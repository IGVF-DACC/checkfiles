# checkfiles on Fargate: implementation plan

> **Status:** approved design, implementation not started (2026-09-11).
> **Prerequisite reading:** `streaming-spike-START-HERE.md` (what streaming was proven, against
> which objects, and the five findings the refactor must not miss). The PoC code the plan ports
> lives in `streaming_spike/`.
>
> **How to use this document.** It is written so that an implementer (person or agent) can
> start from PR 1 in section G without re-deriving the design. Sections A–E are the target
> design, B is the per-format mapping, F is how to test, G is the order of work, H the known
> risks. Anything marked **VERIFY** needs a fact checked at implementation time; anything marked
> **ASK** needs an answer from the team before that step.

## Context

The S3-streaming spike proved every checkfiles format with portal data validates by streaming
from S3, with no FUSE mount and no full download. That removes the reason checkfiles runs on a
right-sized EC2 instance. Two motivations for moving to Fargate:

1. **Continuous processing.** Today a Step Function (`cdk/checkfiles_runner/stacks/runner.py`)
   runs once a day at 04:20 UTC, launches an EC2 instance sized from the pending count, and
   validates everything in one 23-hour `multiprocessing.Pool` run. Submitters wait up to a day.
2. **Resource usage.** When one or two files take hours, the instance idles on 1–2 CPUs.
   Per-file tasks scale out and in independently.

What is validated does not change; verdict payloads were proven byte-identical against the
current checker in the spike (`streaming_spike/compare_local_vs_stream.py`).

## Decisions (made with Otto, 2026-09-11)

| topic | decision |
|---|---|
| core | EventBridge cron → feeder Lambda → SQS (standard) → `QueueProcessingFargateService` |
| feeder | skips if the queue has any messages (visible **and** in-flight); else searches `upload_status=pending` and sends one message per uuid; no Slack post |
| cadence | cron rate is a `config.py` value per environment; tune after tests |
| worker model | one message in flight per task; task stays alive and keeps polling; ECS scale-in protection ON while processing; visibility-timeout heartbeat; service scales on queue depth, min 0 |
| task size | 1 vCPU / 2 GB, max 20 tasks, both in config |
| active upload credentials | task checks as today; if still active: log, delete message, next cron re-enqueues |
| networking | default VPC, public subnets, public IP (as the EC2 instance today) |
| image | `ContainerImage.from_asset('docker/Dockerfile')`, built at `cdk deploy` |
| reference genomes | lazily fetched into ephemeral storage on the first vcf/gvcf/cram a task sees |
| failures | transient (network, portal 5xx, **and our own unexpected exceptions**) → message not deleted → redelivered → DLQ after 3 receives → alarm → Slack via the existing EventBridge bridge; content-invalid → patched as today; validator crash isolated in a child process → invalid |
| pysam / samtools / pyBigWig transport | presigned https URL, re-signed per pass |
| S3 access | bucket list per env in `config.py`; task-role policy generated at deploy |
| cutover | new stacks alongside `RunCheckfilesStepFunction*`; old stacks deleted after soak in a follow-up |
| checker scope | port faithfully from the spike; pyBigWig replaces validateFiles for bigWig/bigBed/bigInteract (accepted drift); one-pass universal checks; bam stays 3 passes (follow-up) |
| CLI | keep `checkfiles.py --uuid` (streaming); **remove batch mode**; `checkfiles_local.py` keeps working on local paths |

### Why these shapes (short)

- **One message in flight per task, task stays alive.** Pulling several messages into one task
  hides them from other tasks while they wait their turn, which fights horizontal scaling.
  Keeping the task alive across messages amortizes image pull and task start. Scale-in
  protection means autoscaling only ever kills idle tasks.
- **Presigned https, not `s3://`, for htslib.** htslib's `hfile_s3` reads only static
  credentials (env vars, `~/.aws/credentials`), not the ECS task-role endpoint. A presigned GET
  honors `Range`, works for public and private buckets, and is also what pyBigWig needs.
  Fallback if it ever proves problematic: export frozen task-role credentials to env vars right
  before each pysam call.
- **Unexpected exceptions are transient.** A bug in our code must never become a file verdict.
  After 3 receives the message lands in the DLQ and Slack gets one alarm; fix, redeploy, redrive.

## What exists today (orientation for the implementer)

- `src/checkfiles/checkfiles.py`: `file_validation(...)` (~L52–176) does size / gzip / md5 /
  content-md5 via `validation_record.file` (a path-bound `file.File`), then dispatches on
  `file_format`: `bam_pysam_check`, `cram_pysam_check`, `validate_files_fastq_check` +
  `fastq_get_average_read_length_and_number_of_reads`, `validate_files_check` (bed / bigWig /
  bigInteract / bigBed / bedpe), `fasta_check`, `check_valid_h5ad_file_format`,
  `tabular_file_check`, `vcf_sequence_check`, `seqspec_file_check`.
  `get_file_validation_record_from_metadata` (~L591) maps `s3_uri` to `$HOME/<bucket>/<key>`
  (the goofys mount). `main()` (~L689) has a `--uuid` mode and a batch mode
  (`multiprocessing.Pool`, `patching_worker`, `fetch_pending_files_metadata`).
  `FileValidationRecord.make_payload()` in `file.py` builds the PATCH body.
- Portal calls are bare `requests` with no timeouts or retries. `fetch_etag_for_uuid` already
  uses `?frame=edit&datastore=database`.
- `checkfiles_local.py` validates a local file; `scripts/checkfiles_local.sh` runs it via the
  Docker Hub image `igvf/checkfiles-local`.
- Tests: `src/tests/`, pytest + pytest-mock, real fixtures in `src/tests/data/`, run from the
  repo root; CircleCI installs the binaries ad hoc and runs `pytest --ignore=cdk --cov .`;
  GitHub Actions runs the CDK snapshot test (`cdk/tests/test_snapshot.py`, pytest-snapshot).
- CDK: `cdk/app.py`, `cdk/checkfiles_runner/stacks/runner.py` (Step Function + 5 Lambdas),
  `cdk/checkfiles_runner/config.py` (flat dict, `_sandbox` / `_production` suffixed keys),
  `cdk/requirements.txt` (aws-cdk-lib 2.222.0). "Sandbox" means the staging account and
  `api.staging.igvf.org`. The `checkfiles-instance` instance profile is **not** in this repo.
- `docker/Dockerfile`: ubuntu 22.04, samtools 1.20 from source, vcf_assembly_checker v0.10.0,
  fastq_stats via cargo, validateFiles, `pip install -r requirements.txt`, bakes the reference
  genomes at build via `utils/download_ref_files.py`, entrypoint `exec "$@"`.
- Spike gotchas the port must preserve (details in the spike docs): multi-member gzip in
  content-md5; open the FIFO before the network read; FastaValidator must run in a subprocess;
  validateFiles on a FIFO does not decompress (decompress upstream) while fastq_stats wants raw
  `.gz`; never name a FIFO `*.gz`; pyBigWig needs https and can hard-abort the process; h5py over
  s3fs blockcache; seqspec via `load_spec_stream`; frictionless needs `frictionless[aws]` for
  `s3://`; missing key and corrupt file are indistinguishable in SamtoolsError / pyBigWig
  messages, so classify with a HEAD probe; a 0-byte reference genome silently yields 0/0 matches.

## A. New and changed modules under `src/checkfiles/`

Modules stay flat (`import file`, `import constants`; tests import `checkfiles.<module>` via the
`sys.path.append` in `src/checkfiles/__init__.py`).

### A1. `s3_source.py` — sources, FIFO bridge, error taxonomy (new)

- `class TransientError(Exception)`: retry later, never a verdict. Raised for S3/portal/network
  failures. Caught only in `worker.process_message` and `checkfiles.main` (`--uuid` → exit 1).
- `class SourceNotFound(FileNotFoundError)`: HEAD 404. Subclasses `FileNotFoundError` so the
  existing `except FileNotFoundError` in `file_validation` still yields `file not found`.
- `is_transient_exception(exc) -> bool`: botocore connection/timeout/streaming errors; `ClientError`
  with HTTP 403/429/5xx or code in `SlowDown`, `Throttling`, `RequestTimeout`, `InternalError`,
  `ServiceUnavailable`; `requests` ConnectionError/Timeout/ChunkedEncodingError.
- `class LocalSource(path)` and `class S3Source(s3_uri, client=None, region, presign_expires)`
  with one interface: `display_path`, `basename`, `size()`, `exists()`, `is_gzipped()` (2-byte
  magic), `open_raw()`, `open_text(decompress, encoding)`, `fifo(decompress, name=None)` (context
  manager yielding a path), `htslib_target()`, `pybigwig_target()`, `frictionless_target()`,
  `h5py_target()`, `local_path()` (download fallback, unused by any checker in this plan).
  - Local: targets are the path; `fifo(decompress=False)` yields the real path (tool messages
    echo it, which existing tests assert); `fifo(decompress=True)` on a `.gz` feeds `gzip.open`
    into a FIFO; on a plain file yields the path.
  - S3: `head()` via HeadObject (404 → `SourceNotFound`, transient → `TransientError`);
    `htslib_target()` / `pybigwig_target()` = `presigned_url()` (fresh per call);
    `frictionless_target()` = `s3://` (S3Loader, task-role creds); `h5py_target()` = `s3fs`
    blockcache file object, 8 MiB blocks, `anon=False`; `open_raw()` / `open_text()` via
    `smart_open`; FIFO named after the object basename minus `.gz` to keep validateFiles
    messages close to today's.
- `as_source(path_or_source)`: `str` → Local or S3 by `s3://` prefix; a source passes through.
- `class FifoStream(opener, name, workdir)`: port of `streaming_spike/validate_bucket4a.py::FifoStream`
  with an opener callable instead of a URL (so LocalSource and tests can feed it) and the
  exception object kept in `.error`. **Invariants from the spike:** open the FIFO for writing
  before calling the opener; never name a FIFO `*.gz`; swallow `BrokenPipeError` (tool exited
  early = a verdict); drain on `__exit__` if the writer is still alive; join with a timeout.

### A2. `streaming_checks.py` — spike code with no existing counterpart (new)

- `scan_stream(fileobj, chunk_size=65536) -> UniversalResult(size, md5sum, is_gzipped, content_md5sum, content_md5_exc)`:
  verbatim port of `streaming_spike/validate_universal.py::universal_checks` (md5 + gzip magic +
  multi-member-aware content md5 in one pass). Truncated gzip → `content_md5_exc = EOFError(...)`
  (mirrors `gzip.open`); `zlib.error` stored, not raised. Pure function, unit-testable on local files.
- `load_chrom_sizes(path)`, `bigwig_check(source, assembly) -> dict`, `bigbed_check(source, assembly) -> dict`
  (bodies from `streaming_spike/validate_bigwig.py` / `validate_bigbed.py`; return `{}` or
  `{'validate_files': '\n'.join(errors)}` so the error key stays what it is today). bigInteract
  uses `bigbed_check`. Unsupported assembly → the same `assembly … is not supported` message
  `validate_files_check` produces.
- `big_check_isolated(kind, source, assembly) -> dict`: runs
  `python -m streaming_checks --isolated <kind> <target> <chrom_sizes>` as a **subprocess** (not
  a fork: the worker has a live heartbeat thread); stdout is the JSON dict; negative return code →
  `{'validate_files': '<kind> reader aborted with signal N; file likely corrupt or truncated'}`;
  positive rc with no JSON → `TransientError` (our crash, not the file's).
- `classify_open_failure(source, exc)`: when pysam / pyBigWig say "could not be opened", call
  `source.exists()`; False or transient → raise `TransientError`; else return so the caller emits
  the invalid verdict as today.

### A3. `references.py` — lazy reference genomes (new)

- `ensure_assembly_reference(assembly, fasta_path) -> str`: return early if `fasta_path` and
  `fasta_path + '.fai'` exist **and are non-empty** (the 0-byte placeholder trap); else, under a
  lock, stream `FILE_URLS[assembly]` (imported from `utils/download_ref_files.py`, not
  duplicated) to `<fasta_path>.gz.part` with `requests` `stream=True` and a timeout, rename,
  `gzip -d`, `pysam.faidx`, assert non-empty. Download failure → `TransientError`; empty result →
  `RuntimeError`. Cached for the process lifetime. (`download_ref_files.py` today reads the whole
  ~900 MB gz into memory and its `exists()` guard is defeated by a 0-byte file; do not copy that.)
- `ensure_portal_reference(reference_file_path, portal_url, portal_auth) -> str` for cram:
  replaces `checkfiles.get_reference_file_path`; GET the reference-file object, take its
  `s3_uri`, stream it to `$REFERENCE_DIR/<accession>.fa` (gunzip on the fly), `pysam.faidx`.
  **Untested (no cram data on the portal).**
- `REFERENCE_DIR` env, default `src/checkfiles/supporting_files` (repo-relative like
  `constants.ASSEMBLY_TO_SEQUENCE_FILE_MAP`; container `WORKDIR /checkfiles`).

### A4. `worker.py` — SQS loop (new)

- `WorkerSettings.from_env()` (see D); `Outcome` enum: `VALIDATED`, `SKIPPED_NOT_PENDING`,
  `SKIPPED_ACTIVE_CREDENTIALS`, `SKIPPED_ETAG_CHANGED`, `INVALID_MESSAGE`, `TRANSIENT`.
- `TaskProtection(agent_uri)`: `PUT {ECS_AGENT_URI}/task-protection/v1/state` with
  `{"ProtectionEnabled": bool, "ExpiresInMinutes": N}`; returns False on failure, never raises;
  no-op with one warning when `ECS_AGENT_URI` is unset (local runs).
- `VisibilityHeartbeat` (context manager, thread): every `heartbeat_interval` →
  `change_message_visibility(VisibilityTimeout=visibility_timeout)` and re-arm protection.
  Stops extending at the SQS 12 h ceiling (log and let the message return).
- `process_message(settings, body) -> Outcome`, in order:
  1. `uuid = body['uuid']` (KeyError → `INVALID_MESSAGE`, delete).
  2. `fetch_file_metadata_by_uuid` now `GET {backend}/{uuid}?datastore=database` (bypasses the
     opensearch indexing lag; 404 → `INVALID_MESSAGE`; transient → `TRANSIENT`).
  3. `upload_status != 'pending'` → `SKIPPED_NOT_PENDING` (this is the duplicate-message guard).
  4. `upload_credentials_are_expired` False → `SKIPPED_ACTIVE_CREDENTIALS`.
  5. `get_file_validation_record_from_metadata` (now builds `file.S3File`); `original_etag = fetch_etag_for_uuid`.
  6. `file_validation(...)`; `TransientError` **or any other exception** → `TRANSIENT` (logged with traceback).
  7. `fetch_etag_for_uuid` again; mismatch → `SKIPPED_ETAG_CHANGED` (delete; "will not patch" as today).
  8. `patch_file`; transient → `TRANSIENT`; 4xx → log → `INVALID_MESSAGE`; else `VALIDATED`.
- `handle_message`: protection ON (if that fails, `change_message_visibility(0)` and return);
  heartbeat; `TRANSIENT` → `change_message_visibility(VisibilityTimeout=transient_retry_delay)`
  and **do not delete**; every other outcome → `delete_message`. Protection OFF only when a
  `receive_message` long-poll comes back empty (the only moment a task is scale-in eligible).
  SIGTERM sets a stop event; the loop exits after the in-flight message; container `stopTimeout` 120 s.
- `main(argv)`: `--self-check` (startup checks, exit 0/3), `--once` (process one message, debug).

### A5. Changes to existing modules

- `file.py`: `File` unchanged plus a `source` property (`LocalSource`). New `S3File(source, file_format)`:
  `path` returns the s3_uri (log lines print `.path`), `size` via HEAD (cached; `SourceNotFound`
  propagates as `FileNotFoundError`), `is_zipped` via a 2-byte read, `md5sum` / `content_md5sum`
  run `scan_stream(source.open_raw())` **once** on first access and cache all four values;
  `content_md5sum` raises `TypeError` if not gzipped (as `File`) and re-raises `content_md5_exc`
  so `file_validation`'s `except (EOFError, zlib.error, gzip.BadGzipFile)` still yields
  `file_content_error`. Stream failures → `TransientError`. Add `get_s3_file(s3_uri, file_format)`.
  `FileValidationRecord` and `make_payload()` unchanged.
- `checkfiles.py`:
  - `file_validation`: `source = validation_record.file.source` replaces `local_file_path`;
    dispatch adds `bigWig` → `big_check_isolated('bigwig', ...)`, `bigBed` / `bigInteract` →
    `big_check_isolated('bigbed', ...)`; `bed` / `bedpe` keep `validate_files_check`; cram uses
    `references.ensure_portal_reference`. Signature unchanged (tests call it positionally).
  - Every checker's first path argument becomes `path_or_source`, starting with
    `source = as_source(...)`; bodies per section B. `get_header_row(source, is_gzipped)` uses
    `source.open_text` and reads only leading lines. `is_zipped(path)` → `as_source(path).is_gzipped()`.
  - Portal calls get `timeout=(10, 60)`, 3 attempts with backoff on connection errors / 5xx,
    then `TransientError`. Implemented as a thin `portal_get(url, auth)` that still calls
    `requests.get` (tests patch `checkfiles.checkfiles.requests.get` and `requests.Session.get`;
    `check_content_md5sum` keeps its `Session`).
  - `get_file_validation_record_from_metadata(file_metadata)`: drop `mount_basedir`, return an
    `S3File`. Delete `make_local_path_from_s3_uri`, `get_reference_file_path`, the goofys `HOME` logic.
  - `main()`: `--uuid` mode only (streams with the caller's AWS credentials; `TransientError` →
    `sys.exit(1)` as today). Remove batch mode, `worker`, `patching_worker`,
    `fetch_pending_files_metadata`, `--number-of-files`, `multiprocessing`.
- `checkfiles_local.py`: passes the local path through; checkers coerce to `LocalSource`; big*
  goes through `big_check_isolated` (same drift); vcf triggers `ensure_assembly_reference` on
  first use (download into the container unless `supporting_files` is volume-mounted).
- `utils/download_ref_files.py`: kept as the offline pre-fetch tool; `references.py` reuses `FILE_URLS`.

## B. Per-format mapping

| check | today | streaming replacement (spike file) | S3 transport | notes |
|---|---|---|---|---|
| size / md5 / content-md5 / gzip magic | `File` (getsize + 2 full reads) | `S3File` + `scan_stream` (`validate_universal.py`) | HEAD, 2-byte read, one full pass | multi-member gzip handled; early returns (size 0, gzip mismatch) skip the full pass |
| bam | `bam_pysam_check`: quickcheck → stats → count | same function on `source.htslib_target()` (`validate_bam.py`) | presigned https, fresh per pass | 3 passes kept; `SamtoolsError` → `classify_open_failure` |
| cram | `cram_pysam_check`: `samtools view -h -T ref \| samtools stats -` | same, ref via `ensure_portal_reference`; samtools must be libcurl-enabled | presigned https | **untested, no data**; keep path, flag in docs |
| fastq | `validate_files_fastq_check` + `fastq_get_average_read_length_and_number_of_reads` | same (`validate_bucket4a.py`) | FIFO decompressed for validateFiles; second FIFO with **raw gz** for fastq_stats | two passes as today |
| bed, bedpe | `validate_files_check` → validateFiles | same (`validate_files_stream`) | FIFO decompressed, named `<basename minus .gz>` | message echoes the FIFO path instead of the goofys path |
| bigWig | `validate_files_check` → `validateFiles -type=bigWig` | `bigwig_check` via `big_check_isolated` (`validate_bigwig.py`) | presigned https via pyBigWig | accepted drift; key stays `validate_files`; crash-isolated |
| bigBed, bigInteract | `validate_files_check` → `validateFiles -type=bigBed*` | `bigbed_check` via `big_check_isolated` (`validate_bigbed.py`) | presigned https via pyBigWig | bigInteract untested; optional `bb.SQL()` vs `src/schemas/as/interact.as` later |
| fasta | `fasta_check`: gunzip to temp, in-process `fasta_validator` | same, validator in a **subprocess** (`validate_fasta_stream`) | FIFO decompressed | GIL deadlock finding from the spike |
| h5ad | `check_valid_h5ad_file_format` | same on `source.h5py_target()` (`validate_h5ad.py`) | s3fs blockcache | local unchanged |
| tsv / csv | `tabular_file_check` | same on `source.frictionless_target()` + streamed header row (`validate_tabular.py`) | `s3://` via frictionless S3Loader | needs `frictionless[aws]` |
| vcf / gvcf | `vcf_sequence_check` → vcf_assembly_checker | same (`validate_vcf_stream`) + `ensure_assembly_reference` | FIFO decompressed | reference fetched once per task, asserted non-empty |
| seqspec | `seqspec_file_check` → `load_spec(path)` | same → `load_spec_stream(io.StringIO(...))` (`validate_seqspec.py`) | in-memory | `spec_fn = source.display_path`; worker sets `IGVF_API_KEY` / `IGVF_SECRET_KEY` |

## C. CDK

### C1. `cdk/checkfiles_runner/config.py` — new keys, `_sandbox` / `_production` each

`feeder_rate_minutes` (15), `fargate_task_cpu` (1024), `fargate_task_memory_mib` (2048),
`fargate_ephemeral_storage_gib` (40), `fargate_max_tasks` (20),
`fargate_create_s3_gateway_endpoint` (False), `s3_buckets` (list), `pysam_probe_url` (a known
public bam, e.g. `IGVFFI3323DCKT`). `portal_secrets_arn_*` and `backend_uri_*` are reused.

**ASK / VERIFY — bucket lists.** The goofys fstab names `igvf-files`, `igvf-files-staging`,
`igvf-restricted-files`, `igvf-restricted-files-staging`; the spike's production `s3_uri`s were
in `igvf-public` and `igvf-private`. Derive each environment's list from the distinct `s3_uri`
prefixes on that portal (`/search?type=File&field=s3_uri&limit=all`) and from the policies on the
`checkfiles-instance` instance profile. A bucket in another account also needs a bucket-policy
grant for the new task role.

### C2. `cdk/checkfiles_runner/stacks/fargate.py` (new)

`CheckfilesFargateProps` dataclass mirroring the keys above plus `docker_context_path='..'`,
`dockerfile_path='docker/Dockerfile'`. `CheckfilesFargate(Stack)` with `Sandbox` / `Production`
subclasses (same pattern as `runner.py`). Resources in order:

1. `Vpc.from_lookup(is_default=True)`; optional S3 gateway endpoint behind the config flag
   (a second endpoint on a route table that has one fails; check `describe-vpc-endpoints` first).
   Commit `cdk/cdk.context.json` after the first deploy.
2. `Cluster`.
3. `dlq = Queue(retention 14 d)`; `queue = Queue(visibility_timeout 15 min, retention 4 d,
   dead_letter_queue=(max_receive_count=3, dlq))`.
4. `SMSecret.from_secret_complete_arn(portal_secrets_arn)`; `LogGroup(retention 1 month)`.
5. `ContainerImage.from_asset(directory=props.docker_context_path, file=props.dockerfile_path, platform=Platform.LINUX_AMD64)`.
6. `QueueProcessingFargateService(cluster, queue, image, cpu, memory_limit_mib, ephemeral_storage_gib,
   command=['python', 'src/checkfiles/worker.py'], environment={QUEUE_URL, BACKEND_URI, S3_REGION,
   PYSAM_PROBE_URL, VISIBILITY_TIMEOUT_SECONDS, HEARTBEAT_INTERVAL_SECONDS, TASK_PROTECTION_MINUTES,
   TRANSIENT_RETRY_DELAY_SECONDS}, secrets={PORTAL_KEY, PORTAL_SECRET_KEY from the secret},
   min_scaling_capacity=0, max_scaling_capacity=max_tasks,
   scaling_steps=[(upper=0, -1), (lower=1, +1), (lower=5, +2), (lower=20, +5)],
   disable_cpu_based_scaling=True, cooldown=2 min, assign_public_ip=True,
   task_subnets=PUBLIC, runtime_platform X86_64/LINUX, enable_execute_command=True,
   log_driver=aws_logs(stream_prefix='checkfiles', log_group))`.
   **VERIFY prop names against aws-cdk-lib 2.222.0** (there was no local CDK install when this
   was written): `ephemeral_storage_gib`, `disable_cpu_based_scaling`, `enable_execute_command`,
   `command`, `cooldown`, `runtime_platform`. Fallbacks via `add_property_override` on the L1
   task definition / service / container. Always set `StopTimeout: 120` on the container by
   override. If CPU scaling cannot be disabled, set `cpu_target_utilization_percent=90`.
7. Task role: `s3:GetObject` on `arn:aws:s3:::{b}/*`, `s3:ListBucket` + `s3:GetBucketLocation`
   on `arn:aws:s3:::{b}` per bucket (ListBucket is what makes a missing key a 404 → "file not
   found", not a 403 → transient); `ecs:UpdateTaskProtection` on `arn:…:task/{cluster_name}/*`.
8. Feeder `PythonFunction(entry='checkfiles_runner/lambdas/feeder', handler='feed_queue',
   timeout 5 min, env {PORTAL_SECRETS_ARN, BACKEND_URI, QUEUE_URL})`; `portal_secrets.grant_read`,
   `queue.grant_send_messages`; `Rule(Schedule.rate(minutes=feeder_rate_minutes), target=LambdaFunction(feeder))`.
9. DLQ → Slack: `Alarm` on `dlq.metric_approximate_number_of_messages_visible(period 5 min, Maximum) > 0`,
   `treat_missing_data=NOT_BREACHING`, `LambdaAction` → tiny `dlq_alarm` Lambda that `put_events`
   `{Source: 'CheckfilesFargate', DetailType: 'CheckfilesDeadLetterQueueAlarm',
   Detail: {metadata: {includes_slack_notification: true}, data: {slack: {text: ':x: *CheckfilesDLQ* |
   N message(s) in the checkfiles dead-letter queue for <backend_uri>; see the DLQ and log group <name>'}}}}`
   (the exact shape `runner.py::make_slack_notification_task` emits). Fires on state transition
   only; recovery = fix, redeploy, redrive the DLQ from the console.
10. `CfnOutput`: queue URL, DLQ URL, cluster, service, log group.

### C3. `cdk/checkfiles_runner/lambdas/feeder/main.py` (+ `requirements.txt`: `requests`)

`get_secret` (copy of `check_pending.get_secret`, with its missing `ClientError` import fixed),
`queue_has_messages(sqs, url)` (Visible + NotVisible > 0), `fetch_pending_uuids(backend, auth)`
(`/search?type=File&upload_status=pending&field=uuid&limit=all`, timeout), `send_uuids`
(`send_message_batch` in chunks of 10, body `{"uuid": ...}`, log failed entries),
`feed_queue(event, context) -> {'skipped', 'enqueued', 'pending'}`.

### C4. `cdk/app.py`, `cdk/README.md`

Instantiate `CheckfilesFargateSandbox` / `CheckfilesFargateProduction` next to the existing stacks
(untouched). README: deploy commands, `cdk.context.json` note, DLQ redrive runbook,
`aws ecs execute-command` for debugging.

## D. Worker container contract

- Entrypoint unchanged (`scripts/entrypoint.sh`, `exec "$@"`); command
  `python src/checkfiles/worker.py`; `WORKDIR /checkfiles`.
- Env: `QUEUE_URL`, `BACKEND_URI` (required); `PORTAL_KEY` / `PORTAL_SECRET_KEY` (ECS secrets;
  copied to `IGVF_API_KEY` / `IGVF_SECRET_KEY` at startup as `main()` does); `ECS_AGENT_URI`
  (agent-provided); `S3_REGION`, `VISIBILITY_TIMEOUT_SECONDS` 900, `HEARTBEAT_INTERVAL_SECONDS` 300,
  `TASK_PROTECTION_MINUTES` 120, `TRANSIENT_RETRY_DELAY_SECONDS` 300, `PRESIGN_EXPIRES_SECONDS` 3600,
  `WORK_DIR` `/tmp/checkfiles`, `REFERENCE_DIR`, `PYSAM_PROBE_URL`, `CHECKFILES_SKIP_STARTUP_CHECKS`, `LOG_LEVEL`.
- Startup checks (`--self-check`): `pyBigWig.remote == 1`; `validateFiles`, `fastq_stats`,
  `vcf_assembly_checker`, `samtools` on PATH; `samtools version` shows `libcurl=yes`;
  `pysam.AlignmentFile(PYSAM_PROBE_URL)` opens (https transport proof); SQS
  `get_queue_attributes` works; `WORK_DIR` / `REFERENCE_DIR` writable. Failure → `SystemExit(3)`
  (a visible crash loop, not silent idling).
- Logging: `logformatter.JsonFormatter`; every line for a message carries `uuid` and `receipt_count`.

## E. Dockerfile, requirements, ignore files

- `docker/Dockerfile`: remove the `IGVF_API_KEY` / `IGVF_SECRET_KEY` build args and the
  `download_ref_files.py` step; build htslib 1.20 with `--enable-libcurl --enable-s3` and samtools
  against it, assert `samtools version | grep libcurl=yes`; keep vcf_assembly_checker,
  fastq_stats, validateFiles (x86_64 prebuilt is fine on Fargate); `pip install --no-binary pyBigWig pyBigWig`
  and assert `pyBigWig.remote == 1`; import-smoke `pysam, s3fs, smart_open, frictionless, FastaValidator`;
  create `supporting_files` and `/tmp/checkfiles` owned by the `checkfiles` user.
- `src/checkfiles/requirements.txt`: `pysam==0.24.1`; add `pyBigWig==0.3.25`, `s3fs==<pinned>`,
  `smart_open[s3]==8.0.1`; `frictionless[aws]==5.18.0`; bump `boto3` / `botocore` to what s3fs's
  `aiobotocore` pins (install s3fs first, then freeze); keep h5py, py-fasta-validator, requests,
  the seqspec git tag `v25-09-23` (the PyPI seqspec has no `seqspec_check`).
- `.dockerignore`: add `streaming_spike`, `*.md`, root `validateFiles` and `*.gz`,
  `src/checkfiles/src/`, `src/checkfiles/supporting_files/*.fa*`, `.github`. This both keeps
  references out of the image and stops a stray multi-GB reference copy in a working tree from
  churning the CDK asset hash.
- `.circleci/config.yml`: `libcurl4-openssl-dev` before pip (pyBigWig builds from source).
- `validate_file_locally.md`: references download on first use in the container, or mount `supporting_files`.

## F. Tests

pytest + pytest-mock + `botocore.stub.Stubber`; no moto. S3 reads exercised by injecting local file objects.

- `src/tests/test_streaming_checks.py`: `scan_stream` equals `File` on `ENCFF594AYI.fastq.gz`,
  `ENCFF206HGF.bam` (bgzf), `ENCFF080HPN.tsv`; a two-member gzip built in-test → md5 of the
  concatenation; a truncated gzip → `EOFError`; `bigwig_check` / `bigbed_check` on tiny committed
  fixtures (bigWig written with pyBigWig in `src/tests/create_minimal_big_files.py`; bigBed
  generated once with `bedToBigBed`); wrong assembly → mismatches; `big_check_isolated` with a
  self-SIGSEGV command → invalid dict; skip remote asserts when `pyBigWig.remote == 0`.
- `src/tests/test_s3_source.py`: URI parsing, `https_url`, `presigned_url`, `head()` 404 →
  `SourceNotFound`, 403 / 503 / `SlowDown` → `TransientError`; `FifoStream` from `io.BytesIO`
  read by `cat` → identical bytes; an opener raising before data → the reader terminates and
  `.error` is set (the deadlock regression test); `LocalSource.fifo(decompress=True)` on gz and
  plain fixtures.
- `src/tests/test_file_s3.py`: `S3File` with `open_raw` / `head` patched to a local fixture equals
  `File`; `file_validation` with an `S3File` over `ENCFF594AYI.fastq.gz` yields the same
  `info` / `errors` as `test_main_fastq` (payload parity).
- `src/tests/test_worker.py`: every `Outcome` of `process_message`; `handle_message` delete vs
  `change_message_visibility(300)`; heartbeat extends at least twice at 0.05 s intervals;
  `TaskProtection` success / failure / unset; `startup_checks` with `which` / pysam patched.
- `src/tests/test_references.py`: non-empty → no download; 0-byte → download path; failure → `TransientError`.
- Feeder: queue non-empty → skipped; 23 uuids → batches of 10 / 10 / 3.
- Existing tests: unchanged except deleting `test_get_reference_file_path`; vcf tests keep
  passing because `ensure_assembly_reference` returns early on the non-empty `chrY_sample.fa`.
- CDK snapshot: `cdk/tests/test_snapshot.py::test_fargate_stack_matches_snapshot` with test props,
  `docker_context_path='tests/fixtures/worker_image'` (a one-line `FROM scratch` Dockerfile for a
  stable asset hash), two dummy buckets, endpoint flag off; `Vpc.from_lookup` resolves to CDK's
  dummy VPC in tests. First run with `pytest --snapshot-update`.

### End-to-end verification on staging

1. Disable the old sandbox cron (`aws events disable-rule` on `RunCheckfilesStateMachineCronRule`; no code change).
2. `worker.py --self-check` inside a task (`aws ecs execute-command`) passes.
3. Submit one good and one bad object per format from `src/tests/data/` on staging; wait for
   credential expiry (or use `--uuid --ignore-active-credentials` for early runs).
4. Watch queue depth, `RunningTaskCount` scaling 0 → N → 0, the log group (uuid, outcome), DLQ stays 0.
5. Verdict comparison: for 20–30 already-validated staging files run
   `checkfiles.py --uuid X --server https://api.staging.igvf.org` (no `--patch`, laptop AWS
   creds) and diff `make_payload()` against the portal's stored fields. Expect byte-identical
   except the path echoed in validateFiles messages and the big* checker text.
6. Force a transient failure (temporarily drop `s3:GetObject` on one bucket) → message cycles 3
   times → DLQ → Slack arrives; restore, redrive, confirm.
7. Soak ≥ 1 week on sandbox; deploy production; disable the production cron; soak; decommission.

## G. Ordered implementation steps (PR-sized)

1. **PR 1 — sources and streaming core** (no behavior change): `s3_source.py`,
   `streaming_checks.py`, `references.py`, `requirements.txt`, `.circleci/config.yml`, new tests +
   big* fixtures. Done: new tests green; `scan_stream` matches `File` incl. multi-member;
   existing tests green.
2. **PR 2 — transport-agnostic checkers**: `file.py` (`S3File`), `checkfiles.py` (checkers accept
   path-or-source, dispatch incl. big* via pyBigWig, portal timeouts / `TransientError`,
   `?datastore=database`, S3-based record, delete goofys helpers and batch mode),
   `checkfiles_local.py`, `test_file_s3.py`. Done: `pytest --ignore=cdk` green;
   `checkfiles.py --uuid` works from a laptop against a real staging object of each format that
   has data.
3. **PR 3 — worker + image**: `worker.py`, `docker/Dockerfile`, `.dockerignore`,
   `validate_file_locally.md`, `test_worker.py`. Done: image builds with its asserts;
   `worker.py --self-check` exits 0 with real creds; `--once` processes a hand-enqueued message.
4. **PR 4 — CDK**: `stacks/fargate.py`, `lambdas/feeder/`, `lambdas/dlq_alarm/`, `config.py`,
   `app.py`, snapshot test + fixture, `cdk/README.md`, `cdk.context.json`. Done: `pytest` in
   `cdk/` green; `cdk deploy CheckfilesFargateSandbox --profile igvf-staging` succeeds; a task
   reaches RUNNING and passes startup checks. Old stacks untouched.
5. **PR 5 — staging verification and tuning**: config values after observation, README runbook.
   Done: end-to-end steps 1–6 recorded, DLQ → Slack proven.
6. **PR 6 — production**: deploy, disable the production cron, one-week soak with the DLQ empty
   and spot-checks matching.
7. **Follow-up — decommission**: remove `RunCheckfilesStepFunction*`, the five EC2 lambdas,
   `packer/`, the old snapshot and config keys; `cdk destroy` the old stacks; move
   `streaming_spike/` to `docs/` or delete it.

## H. Open risks / follow-ups

- **bam 3 passes**: 3x egress; collapse to one `AlignmentFile` pass after parity is proven.
- **cram and bigInteract untested**: no portal data; code paths kept and flagged.
- **big* semantic drift**: header chromosome lengths vs per-feature `chromEnd`; documented, accepted.
- **Presigned URL expiry**: task-role credentials cap validity; re-signing per pass covers bam; a
  single multi-hour pass would need the env-var credential fallback.
- **SQS 12 h visibility ceiling**: a 200 GB md5 pass is 0.5–2.2 h, fine; the heartbeat must stop at the cap.
- **Scale-in race**: protection turned off after an empty poll, then a message arrives as ECS
  stops the task; mitigated by returning the message when the protection call fails, plus
  `maxReceiveCount=3`.
- **Feeder starvation**: "any message → skip" means one stuck message delays new enqueues up to
  3 visibility windows; watch during the soak.
- **S3 gateway endpoint** on the looked-up default VPC: optional, verify none exists first.
- **Image size**: the single-stage build keeps toolchains; multi-stage would speed cold scale-out.
- **boto3 bump** forced by s3fs / aiobotocore; smoke-test in the image.
- **vcf via `pysam.VariantFile`** could drop vcf_assembly_checker, the FIFO and the 6 GB
  reference; separate project.

### Critical files

- `src/checkfiles/checkfiles.py`, `src/checkfiles/file.py`
- `streaming_spike/validate_bucket4a.py` (FifoStream and the 4a ports), `validate_universal.py`,
  `validate_bigwig.py`, `validate_bigbed.py`, `validate_tabular.py`, `validate_seqspec.py`,
  `validate_h5ad.py`, `validate_bam.py`
- `cdk/checkfiles_runner/stacks/runner.py` (Slack event shape, PythonFunction / secret
  conventions), `cdk/checkfiles_runner/config.py`, `cdk/app.py`, `cdk/tests/test_snapshot.py`
- `docker/Dockerfile`, `src/checkfiles/requirements.txt`, `.dockerignore`
