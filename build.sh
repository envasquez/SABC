#!/usr/bin/env bash
set -e

find . -name "*.pyc" -type f -delete
find . -path "*/migrations/*.py" -not -name "__init__.py" -delete
find . -name "db.sqlite3" -type f -delete

docker-compose down
docker volume rm sabc_sabc-app || true
docker image rm sabc_sabc || true
docker image prune -f || true
docker-compose up -d --build --force-recreate sabc