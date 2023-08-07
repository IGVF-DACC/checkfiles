#!/bin/bash
set -ex

sudo apt-get update
sudo apt-get -y install \
    python3-pip \
    python3-venv \
    build-essential \
    libbz2-dev \
    liblzma-dev \
    curl \
    zlib1g-dev \
    libsqlite3-dev \
    fuse \
    awsli \
    jq
