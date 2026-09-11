#!/usr/bin/env bash
# Run the Bucket 4a streaming proofs inside the spike image.
#
# Build first:
#   docker build -f streaming_spike/docker/Dockerfile.spike -t checkfiles-spike:4a .
#
# The repo is bind-mounted at /checkfiles so the repo-relative paths in
# src/checkfiles/constants.py (chrom.sizes, .as schemas, assembly reports) resolve.
#
# The vcf proofs need the reference genomes (grch38.fa / grcm39.fa + .fai) at the path
# ASSEMBLY_TO_SEQUENCE_FILE_MAP expects: src/checkfiles/supporting_files/ (gitignored;
# fetch with utils/download_ref_files.py, as docker/Dockerfile does). If they are there
# the repo mount already covers them. As a fallback, a copy left at the non-canonical
# src/checkfiles/src/checkfiles/supporting_files/ is bind-mounted into place.
#
# Gotcha: bind-mounting a file onto a path that does not exist makes docker create a
# 0-byte placeholder there on the host, which then survives the run. So "present" means
# NON-EMPTY (-s), otherwise a placeholder shadows the real reference and
# vcf_assembly_checker silently reports 0/0 matches.
set -euo pipefail
REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
CANON="$REPO/src/checkfiles/supporting_files"
ALT="$REPO/src/checkfiles/src/checkfiles/supporting_files"
ARGS=(--rm -v "$REPO:/checkfiles" -w /checkfiles)
for f in grch38.fa grch38.fa.fai grcm39.fa grcm39.fa.fai; do
    if [ ! -s "$CANON/$f" ] && [ -s "$ALT/$f" ]; then
        ARGS+=(-v "$ALT/$f:/checkfiles/src/checkfiles/supporting_files/$f:ro")
    fi
done
exec docker run "${ARGS[@]}" checkfiles-spike:4a \
    python3 -u streaming_spike/validate_bucket4a.py "$@"
