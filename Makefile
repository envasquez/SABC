SHELL := /bin/bash
SETUP := SETUP
PROJECT := sabc

.PHONY: clean clean-migrations clean-docker clean-all docker lint test webapp mypy isort destroy-db
.DEFAULT_GOAL: help
export PYTHONPATH=$(shell pwd)/sabc

isort:
	isort .

clean:
	find $(PROJECT) -name "*.pyc" -type f -delete
	find $(PROJECT) -name "__pycache__" -type d -delete
	docker image prune -f

clean-migrations: clean
	find $(PROJECT) -path "*/migrations/*.py" -not -name "__init__.py" -delete

clean-docker:
	docker compose down
	docker image rm sabc_sabc || true
	docker image prune -f

destroy-db:
	docker compose down
	docker volume rm sabc_sabc_app || true
	docker volume rm sabc_postgres_data || true

clean-all: clean-docker clean clean-migrations

webapp: DEPLOYMENT_HOST=db
webapp:
	docker compose down
	docker volume rm sabc_sabc_app || true
	docker image rm sabc_sabc || true
	docker compose -f docker-compose.yml up -d --build

test: clean-migrations
	docker build -f Dockerfile_pytest -t test_sabc .
	docker run --rm test_sabc

mypy: clean-migrations
	docker build -f Dockerfile_mypy -t mypy_sabc .
	docker run --rm mypy_sabc

lint: clean clean-migrations isort
	# DJANGO_SETTINGS_MODULE=sabc.settings python3 -m pylint --load-plugins pylint_django --verbose sabc/tournaments/ sabc/users/ sabc/polls/ --rcfile pyproject.toml
	docker build -f Dockerfile_pylint -t pylint_sabc .
	docker run --rm pylint_sabc

format:
	find . -name "*.py" | xargs black -v
	isort .

make ci: format lint mypy test

help:
	@echo -e "\t make clean"
	@echo -e "\t\t clean pycache, pyc files"
	@echo -e "\t make clean-db"
	@echo -e "\t\t clean migration and database files WARNING: DESTROYS ALL DB DATA!!!!"
	@echo -e "\t clean-docker"
	@echo -e "\t\t clean docker volumes and images"
	@echo -e "\t make clean-all"
	@echo -e "\t\t runs all clean targets"
	@echo -e "\t make docker-rebuild"
	@echo -e "\t\t builds the docker container image and starts it"
	@echo -e "\t make lint"
	@echo -e "\t\t runs pylint"