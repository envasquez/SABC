SHELL := /bin/bash -e
PYTHON := python3
PROJECT := sabc
POETRY_ENV_BIN := $(shell poetry env info --path)/bin
CURRENT_PATH := $(PATH)
PATH := $(POETRY_ENV_BIN):$(PATH)

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

.PHONY: clean lint format

clean:
	find $(PROJECT) -name "*.pyc" -type f -delete
	find $(PROJECT) -name "__pycache__" -type d -delete

lint: clean
	ruff check --select I --fix sabc $(VERBOSE) && \
	PYRIGHT_PYTHON_FORCE_VERSION="latest" pyright $(VERBOSE)

format:
	ruff format $(VERBOSE) .
