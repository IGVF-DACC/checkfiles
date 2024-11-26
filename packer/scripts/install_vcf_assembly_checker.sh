#!/bin/bash
set -ex
sudo apt-get install cmake wget build-essential libboost-all-dev -y
sudo wget https://github.com/EBIvariation/vcf-validator/releases/download/v0.10.0/vcf_assembly_checker_linux
sudo chmod 755 vcf_assembly_checker_linux
sudo cp vcf_assembly_checker_linux /usr/bin/vcf_assembly_checker
