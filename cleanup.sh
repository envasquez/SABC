#!/usr/bin/bash

docker system prune -f
sudo journalctl --vacuum-time=7d
sudo apt clean