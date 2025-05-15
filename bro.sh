#!/bin/bash

# Update system packages
apt update 

# Install Hydra and Nmap
apt install -y hydra nmap

# Install required Python modules
pip3 install nmap requests

# Run your scripts
python3 rz.py
