#!/usr/bin/bash

 docker compose -f docker-compose.prod.yml down && \
    git pull && \
    docker compose -f docker-compose.prod.yml build --no-cache && \
    docker compose -f docker-compose.prod.yml up -d && \
    docker system prune -f && \
    sudo journalctl --vacuum-time=7d && \
    sudo apt clean
