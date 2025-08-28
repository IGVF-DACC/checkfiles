#!/bin/bash
set -ex

sudo apt-get update
sudo apt-get -y install \
    software-properties-common \
    build-essential \
    libbz2-dev \
    liblzma-dev \
    curl \
    zlib1g-dev \
    libsqlite3-dev \
    fuse \
    awscli \
    jq

# Install Python 3.12
sudo add-apt-repository -y ppa:deadsnakes/ppa
sudo apt-get -y install python3.12 python3.12-pip python3.12-venv python3.12-dev
