SHELL := /bin/bash
SETUP := SETUP
PROJECT := sabc

.PHONY: clean clean-db clean-docker clean-all docker lint test
.DEFAULT_GOAL: help
export PYTHONPATH=$(shell pwd)/sabc

clean:
	find $(PROJECT) -name "*.pyc" -type f -delete
	find $(PROJECT) -name "__pycache__" -type d -delete

clean-db: clean
	find $(PROJECT) -path "*/migrations/*.py" -not -name "__init__.py" -delete

clean-docker:
	docker compose down
	docker volume rm sabc_sabc_app || true
	docker volume rm sabc_postgres_data || true
	docker image rm sabc_sabc || true
	docker image prune -f

clean-all: clean-docker clean clean-db

docker: DEPLOYMENT_HOST=db
docker: clean-all
	docker compose up -d --build --force-recreate

test-webapp: DEPLOYMENT_HOST=db
test-webapp:
	docker-compose down
	docker volume rm sabc_sabc_app || true
	docker image rm sabc_sabc || true
	docker compose up -d --build

lint: clean clean-db
	python3 -m pylint --verbose --rcfile=.pylintrc --output=pylint.out sabc/tournaments; cat pylint.out

test: clean clean-db
	python3 sabc/manage.py makemigrations && python3 sabc/manage.py migrate --run-syncdb
	python3 -m coverage run --branch --source=sabc/tournaments sabc/./manage.py test --verbosity=2 sabc
	python3 -m coverage report

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