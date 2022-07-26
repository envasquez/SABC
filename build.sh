#!/usr/bin/env bash
set -e

find . -name "*.pyc" -type f -delete
find . -path "*/migrations/*.py" -not -name "__init__.py" -delete

docker-compose down
docker-compose up -d --build --force-recreate sabc