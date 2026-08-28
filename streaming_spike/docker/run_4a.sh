#!/usr/bin/env bash
# Run the Bucket 4a streaming proofs inside the spike image.
#
# Build first:
#   docker build -f streaming_spike/docker/Dockerfile.spike -t checkfiles-spike:4a .
#
# The repo is bind-mounted at /checkfiles so the repo-relative paths in
# src/checkfiles/constants.py (chrom.sizes, .as schemas, assembly reports) resolve.
# The reference genomes live at src/checkfiles/src/checkfiles/supporting_files/ in this
# working tree, but ASSEMBLY_TO_SEQUENCE_FILE_MAP expects them at
# src/checkfiles/supporting_files/, so they are mounted individually into place.
set -euo pipefail
REPO="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
REFS="$REPO/src/checkfiles/src/checkfiles/supporting_files"
ARGS=(--rm -v "$REPO:/checkfiles" -w /checkfiles)
for f in grch38.fa grch38.fa.fai grcm39.fa grcm39.fa.fai; do
    [ -f "$REFS/$f" ] && ARGS+=(-v "$REFS/$f:/checkfiles/src/checkfiles/supporting_files/$f:ro")
done
exec docker run "${ARGS[@]}" checkfiles-spike:4a \
    python3 -u streaming_spike/validate_bucket4a.py "$@"
