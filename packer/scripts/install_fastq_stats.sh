#!/bin/bash
set -ex

sudo apt-get update
sudo apt-get -y install rust-1.82-all

git clone https://github.com/IGVF-DACC/fastq_stats.git
cd fastq_stats
cargo-1.82 build --release
sudo cp target/release/fastq_stats /usr/bin
sudo chmod 755 /usr/bin/fastq_stats
