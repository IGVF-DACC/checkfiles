#!/bin/bash
set -ex
sudo mkdir /home/ubuntu/igvf-files
sudo mkdir /home/ubuntu/igvf-files-staging
sudo mkdir /home/ubuntu/igvf-restricted-files
sudo mkdir /home/ubuntu/igvf-restricted-files-staging
sudo chmod 755 /home/ubuntu/igvf-files
sudo chmod 755 /home/ubuntu/igvf-files-staging
sudo chmod 755 /home/ubuntu/igvf-restricted-files
sudo chmod 755 /home/ubuntu/igvf-restricted-files-staging

sudo echo "goofys#igvf-files   /home/ubuntu/igvf-files        fuse     _netdev,allow_other,--file-mode=0666    0       0" | sudo tee -a /etc/fstab
sudo echo "goofys#igvf-files-staging   /home/ubuntu/igvf-files-staging        fuse     _netdev,allow_other,--file-mode=0666    0       0" | sudo tee -a /etc/fstab
sudo echo "goofys#igvf-restricted-files   /home/ubuntu/igvf-restricted-files        fuse     _netdev,allow_other,--file-mode=0666    0       0" | sudo tee -a /etc/fstab
sudo echo "goofys#igvf-restricted-files-staging   /home/ubuntu/igvf-restricted-files-staging        fuse     _netdev,allow_other,--file-mode=0666    0       0" | sudo tee -a /etc/fstab
