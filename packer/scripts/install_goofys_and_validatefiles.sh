#!/bin/bash
set -ex
sudo curl -sS -L -o /usr/local/bin/goofys https://github.com/kahing/goofys/releases/download/v0.24.0/goofys
sudo chmod +x /usr/local/bin/goofys
sudo curl -sS -L -o /usr/local/bin/validateFiles https://raw.githubusercontent.com/IGVF-DACC/validateFiles/main/validateFiles
sudo chmod +x /usr/local/bin/validateFiles
