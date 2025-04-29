#!/bin/bash
set -ex
sudo apt-get update
sudo apt-get install -y libncurses-dev libbz2-dev liblzma-dev libcurl4-openssl-dev
sudo wget https://github.com/samtools/samtools/releases/download/1.20/samtools-1.20.tar.bz2
tar xvjf samtools-1.20.tar.bz2
cd samtools-1.20/
sudo make
sudo make install
