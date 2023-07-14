#!/bin/bash
set -ex

sudo apt-get update
sudo apt-get -y install \
    rustc \
    cargo

git clone https://github.com/IGVF-DACC/fastq_stats.git
cd fastq_stats
cargo build
sudo cp target/debug/fastq_stats /usr/bin
sudo chmod 755 /usr/bin/fastq_stats
