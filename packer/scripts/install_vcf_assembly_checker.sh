#!/bin/bash
set -ex
sudo apt-get install cmake wget build-essential libboost-all-dev -y
sudo wget https://raw.githubusercontent.com/IGVF-DACC/vcfAssemblyChecker/main/vcf_assembly_checker
chmod +x vcf_assembly_checker
