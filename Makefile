.DEFAULT_GOAL := help

export COMPOSE_DOCKER_CLI_BUILD=1
export DOCKER_BUILDKIT=1
export BUILDKIT_PROGRESS=plain

A3M_PIPELINE_DATA ?= $(CURDIR)/hack/compose-volume

CURRENT_UID := $(shell id -u)
CURRENT_GID := $(shell id -g)

define compose
	docker compose -f docker-compose.yml $(1)
endef

define compose_run
	$(call compose, \
		run \
		--rm \
		--user=$(CURRENT_UID):$(CURRENT_GID) \
		--workdir /a3m \
		--no-deps \
		$(1))
endef

.PHONY: shell
shell:  ## Open a shell in a new container.
	$(call compose_run, \
		--entrypoint bash \
		a3m)

.PHONY: build
build:  ## Build containers.
	$(call compose, \
		build \
		--build-arg USER_ID=$(CURRENT_UID) \
		--build-arg GROUP_ID=$(CURRENT_GID))

.PHONY: create-volume
create-volume:  ## Create external data volume.
	mkdir -p ${A3M_PIPELINE_DATA}
	docker volume create \
		--opt type=none \
		--opt o=bind \
		--opt device=$(A3M_PIPELINE_DATA) \
			a3m-pipeline-data

.PHONY: manage
manage:  ## Run Django /manage.py on a3m, suppling <command> [options] as value to ARG, e.g., `make manage ARG=shell`
	$(call compose_run, \
		--entrypoint /a3m/manage.py \
		a3m \
			$(ARG))

.PHONY: bootstrap
bootstrap:  ## Bootstrap a3m (new database).
	$(MAKE) manage ARG="migrate --noinput"

.PHONY: makemigrations
makemigrations:  ## Make Django migrations.
	$(MAKE) manage ARG="makemigrations main fpr"

.PHONY: stop
stop:  ## Stop services
	docker-compose stop a3m

.PHONY: restart
restart:  ## Restart services
	docker-compose restart a3m

.PHONY: pip-compile
pip-compile:  ## Compile pip requirements
	$(call compose_run, \
		--entrypoint=pip-compile \
		a3m \
			--output-file=requirements.txt setup.py)
	$(call compose_run, \
		--entrypoint=pip-compile \
		a3m \
			--output-file=requirements-dev.txt --extra=dev setup.py)

.PHONY: pip-upgrade
pip-upgrade:  ## Upgrade pip requirements
	$(call compose_run, \
		--entrypoint=pip-compile \
		a3m \
			--upgrade --output-file requirements.txt)
	$(call compose_run, \
		--entrypoint=pip-compile \
		a3m \
			--extra dev --upgrade --output-file requirements-dev.txt)

.PHONY: db
db:
	$(call compose_run, \
		--entrypoint=sqlite3 \
		a3m \
			./hack/compose-volume/db.sqlite)

.PHONY: flush
flush: stop flush-db flush-shared-dir bootstrap restart  ## Delete ALL user data.

.PHONY: flush-db
flush-db:  ## Flush SQLite database.
	$(call compose_run, \
		--entrypoint sh \
		a3m \
			-c "rm -rf /home/a3m/.local/share/a3m/db.sqlite")

.PHONY: flush-shared-dir
flush-shared-dir:  ## Flush shared directory including the database.
	$(call compose_run, \
		--entrypoint sh \
		a3m \
			-c "rm -rf /home/a3m/.local/share/a3m/share/")

.PHONY: amflow
amflow:  ## Display the workflow in amflow.
	docker run \
		--rm \
		-p 2323:2323 \
		-v $(PWD)/a3m/assets/workflow.json:/workflow.json \
		artefactual/amflow:latest \
			edit --file=/workflow.json

.PHONY: buf
buf:
	docker run \
		--volume "$(CURDIR)/proto:/workspace" \
		--workdir /workspace \
		bufbuild/buf:1.4.0 \
			$(ARG)

.PHONY: help
help:  ## Print this help message.
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-30s\033[0m %s\n", $$1, $$2}'

.PHONY: publish
publish: publish-clean  ## Publish to PyPI
	pip install --upgrade twine wheel
	python setup.py sdist
	python setup.py bdist_wheel --universal
	twine check dist/*
	twine upload dist/* -r pypi

.PHONY: publish-clean
publish-clean:
	rm -rf a3m.egg-info/
	rm -rf build/
	rm -rf dist/

RED := \033[0;31m
GREEN := \033[0;32m
YELLOW := \033[0;33m
RESET := \033[0m
define print_color
	@echo "$(1)$(2)$(RESET)"
endef

.PHONY: workflow
workflow:  ## Open amflow application web server.
	$(call print_color,$(YELLOW),Connect to http://127.0.0.1:2323)
	@docker run --rm --publish=2323:2323 --pull=always --volume=$(CURDIR)/a3m/assets/workflow.json:/tmp/workflow.json artefactual/amflow:latest edit --file=/tmp/workflow.json --verbosity=warn
