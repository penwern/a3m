.DEFAULT_GOAL := help

A3M_PIPELINE_DATA ?= $(HOME)/.a3m/a3m-pipeline-data

CURRENT_UID := $(shell id -u)


build:  ## Build and recreate containers.
	env COMPOSE_DOCKER_CLI_BUILD=1 DOCKER_BUILDKIT=1 docker-compose build
	env COMPOSE_DOCKER_CLI_BUILD=1 DOCKER_BUILDKIT=1 docker-compose up -d --force-recreate

create-volumes:  ## Create external data volumes.
	mkdir -p ${A3M_PIPELINE_DATA}
	docker volume create \
		--opt type=none \
		--opt o=bind \
		--opt device=$(A3M_PIPELINE_DATA) \
			a3m-pipeline-data

bootstrap:  ## Bootstrap a3m (new database).
	docker-compose run --rm --no-deps --entrypoint /a3m/manage.py a3m-server migrate --noinput

manage:  ## Run Django /manage.py on a3m, suppling <command> [options] as value to ARG, e.g., `make manage-a3m ARG=shell`
	docker-compose run --rm --no-deps --entrypoint /a3m/manage.py a3m-server $(ARG)

migrations:  # Make Django migrations.
	docker-compose run --rm --user=$(CURRENT_UID) --entrypoint=/a3m/manage.py a3m-server makemigrations

logs:
	docker-compose logs -f

restart:  # Restart services
	docker-compose restart a3m-server
	docker-compose restart a3m-client

compile-requirements:  ## Run pip-compile
	pip-compile --output-file requirements.txt requirements.in
	pip-compile --output-file requirements-dev.txt requirements-dev.in

flush: flush-db flush-shared-dir bootstrap restart  ## Delete ALL user data.

flush-db:
	docker-compose run --rm --no-deps --entrypoint /a3m/manage.py a3m-server flush --noinput

flush-shared-dir:  ## Delete contents of the shared directory data volume.
	rm -rf ${A3M_PIPELINE_DATA}/*

amflow:  # See workflow.
	amflow edit --file=a3m/assets/workflow.json

help:  ## Print this help message.
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-30s\033[0m %s\n", $$1, $$2}'
