#!/bin/bash
# Docker wrapper for checkfiles_local.py
# Usage: ./checkfiles_local.sh --tag v23 --input_file_path /path/to/file.bam --file_format bam [other args]

set -e

# Default values
TAG="latest"
INPUT_FILE_PATH=""
DOCKER_IMAGE="igvf/checkfiles-local"

# Parse arguments to extract --tag and --input_file_path
ARGS=()
while [[ $# -gt 0 ]]; do
    case $1 in
        --tag)
            TAG="$2"
            shift 2
            ;;
        --input_file_path)
            INPUT_FILE_PATH="$2"
            shift 2
            ;;
        *)
            ARGS+=("$1")
            shift
            ;;
    esac
done

# Validate required arguments
if [[ -z "$INPUT_FILE_PATH" ]]; then
    echo "Error: --input_file_path is required"
    exit 1
fi

# Check if input file exists
if [[ ! -f "$INPUT_FILE_PATH" ]]; then
    echo "Error: Input file does not exist: $INPUT_FILE_PATH"
    exit 1
fi

# Extract filename from input path
FILENAME=$(basename "$INPUT_FILE_PATH")

# Build the docker run command
docker run --platform linux/amd64 \
    -v "$INPUT_FILE_PATH:/input_data/$FILENAME:ro" \
    "$DOCKER_IMAGE:$TAG" \
    python src/checkfiles/checkfiles_local.py \
    --input_file_path "/input_data/$FILENAME" \
    "${ARGS[@]}" 