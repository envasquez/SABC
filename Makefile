SHELL := /bin/bash -e
PYTHON := python3
PROJECT := sabc
CURRENT_PATH := $(PATH)

DEBUG =
VERBOSE =
NO_CAPTURE =
ifdef DEBUG
	VERBOSE := --verbose
	LOG_LEVEL := DEBUG
	NO_CAPTURE := --capture=no
else
	LOG_LEVEL := INFO
endif

.PHONY: clean format lint test

clean:
	find $(PROJECT) -name "*.pyc" -type f -delete
	find $(PROJECT) -name "__pycache__" -type d -delete
	ruff clean

format:
	ruff format $(VERBOSE) .

lint: clean
	ruff check --select I --fix $(PROJECT) $(VERBOSE)
	PYRIGHT_PYTHON_FORCE_VERSION="latest" pyright $(VERBOSE)

test: clean
	docker build -f Dockerfile.tests -t test_sabc . --no-cache
	docker run test_sabc

webapp: clean
	docker compose down
	docker compose -f deploy/docker-compose.yml up --build
