#!/bin/bash
set -ex

# Install the Rust toolchain via rustup. The distro rust packages lag behind the
# minimum rustc version required by fastq_stats dependencies, and the distro cargo
# links against the system libgit2, which is older than the version cargo expects.
# rustup ships a cargo with libgit2 statically vendored.
curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs \
    | sh -s -- -y --profile minimal --default-toolchain 1.89.0
source "$HOME/.cargo/env"

git clone https://github.com/IGVF-DACC/fastq_stats.git
cd fastq_stats
cargo build --release --locked
sudo cp target/release/fastq_stats /usr/bin
sudo chmod 755 /usr/bin/fastq_stats
