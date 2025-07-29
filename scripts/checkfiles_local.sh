#!/bin/bash
# Docker wrapper for checkfiles_local.py
# Usage: ./checkfiles_local.sh --tag v23 --input_file_path /path/to/file.bam --file_format bam [other args]

set -e

# Default values
TAG="latest"
INPUT_FILE_PATH=""
DOCKER_IMAGE="igvf/checkfiles-local"
IGVF_API_KEY=""
IGVF_SECRET_KEY=""

# Parse arguments to extract --tag, --input_file_path, and IGVF credentials
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
        --igvf-api-key)
            IGVF_API_KEY="$2"
            shift 2
            ;;
        --igvf-secret-key)
            IGVF_SECRET_KEY="$2"
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

# Validate IGVF credentials (both or neither)
if [[ -n "$IGVF_API_KEY" && -z "$IGVF_SECRET_KEY" ]] || [[ -z "$IGVF_API_KEY" && -n "$IGVF_SECRET_KEY" ]]; then
    echo "Error: Both --igvf-api-key and --igvf-secret-key must be provided together"
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
DOCKER_CMD="docker run --platform linux/amd64 -v $INPUT_FILE_PATH:/input_data/$FILENAME:ro"

# Add IGVF credentials as environment variables if provided
if [[ -n "$IGVF_API_KEY" && -n "$IGVF_SECRET_KEY" ]]; then
    DOCKER_CMD="$DOCKER_CMD -e IGVF_API_KEY=$IGVF_API_KEY -e IGVF_SECRET_KEY=$IGVF_SECRET_KEY"
fi

# Complete the docker command
DOCKER_CMD="$DOCKER_CMD $DOCKER_IMAGE:$TAG python src/checkfiles/checkfiles_local.py --input_file_path /input_data/$FILENAME"

# Execute the docker command
echo "Executing: $DOCKER_CMD ${ARGS[@]}"
$DOCKER_CMD "${ARGS[@]}"
