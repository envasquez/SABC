SHELL := /bin/bash
SETUP := SETUP
PROJECT := sabc

.PHONY: clean
.DEFAULT_GOAL: help
export PYTHONPATH=$(shell pwd)/sabc

clean:
	find $(PROJECT) -name "*.pyc" -type f -delete
	find $(PROJECT) -name "__pycache__" -type d -delete

clean-db: clean
	find $(PROJECT) -name "db.sqlite3" -type f -delete
	find $(PROJECT) -path "*/migrations/*.py" -not -name "__init__.py" -delete

clean-docker:
	docker-compose down
	docker volume rm sabc_sabc-app || true
	docker image rm sabc_sabc || true
	docker image prune -f

clean-all: clean clean-db clean-docker

docker-rebuild: clean-all
	docker-compose up -d --build --force-recreate sabc

lint:
	pylint --verbose --rcfile=.pylintrc $(PROJECT)/sabc $(PROJECT)/tournaments $(PROJECT)/users

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