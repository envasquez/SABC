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
	export UNITTEST=1 && \
	export DJANGO_SETTINGS_MODULE="sabc.settings" && \
	cd sabc && \
	python manage.py makemigrations --no-input && \
	python manage.py migrate --run-syncdb && \
	coverage run --branch --source=. -m pytest --capture=no -vv && \
	coverage report --show-missing

webapp: clean
	@echo "Docker webapp target removed - use 'nix develop' then 'start-db' and 'dev-server' instead"
