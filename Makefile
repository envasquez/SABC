SHELL := /bin/bash -e
PYTHON := python3
PROJECT := sabc
POETRY_ENV_BIN := $(shell poetry env info --path)/bin
CURRENT_PATH := $(PATH)
PATH := $(POETRY_ENV_BIN):$(PATH)


.PHONY: clean lint format


clean:
	find $(PROJECT) -name "*.pyc" -type f -delete
	find $(PROJECT) -name "__pycache__" -type d -delete

lint: clean
	pyright

format:
	ruff check . --fix --verbose
