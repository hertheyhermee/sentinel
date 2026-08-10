# Sentinel developer entrypoints.
#
# A Makefile keeps the same commands working locally and in CI, so nobody has to
# remember long docker/pytest invocations and CI cannot drift from local usage.

SHELL := /bin/bash
VENV := .venv
PY := $(VENV)/bin/python
PIP := $(VENV)/bin/pip
RUFF := $(VENV)/bin/ruff
COMPOSE := docker compose

.DEFAULT_GOAL := help

.PHONY: help
help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) \
		| awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-18s\033[0m %s\n", $$1, $$2}'

# ---------------------------------------------------------------------------
# Local environment
# ---------------------------------------------------------------------------

.PHONY: venv
venv: ## Create the virtualenv and install dev dependencies
	python3.12 -m venv $(VENV)
	$(PIP) install --upgrade pip
	$(PIP) install -r requirements/dev.txt

.PHONY: hooks
hooks: ## Install pre-commit git hooks
	pre-commit install

.PHONY: env
env: ## Create .env from the example if missing
	@test -f .env || (cp .env.example .env && echo "created .env")

# ---------------------------------------------------------------------------
# Quality gates (identical commands run in CI)
# ---------------------------------------------------------------------------

.PHONY: lint
lint: ## Run ruff lint and format checks
	$(RUFF) check .
	$(RUFF) format --check .

.PHONY: fmt
fmt: ## Auto-fix lint issues and format code
	$(RUFF) check --fix .
	$(RUFF) format .

.PHONY: typecheck
typecheck: ## Run mypy
	$(VENV)/bin/mypy libs services

.PHONY: test
test: ## Run tests with coverage gate
	$(PY) -m pytest

.PHONY: check
check: lint test ## Everything CI enforces

# ---------------------------------------------------------------------------
# Stack
# ---------------------------------------------------------------------------

.PHONY: up
up: env ## Build and start the full stack
	$(COMPOSE) up -d --build
	@echo "API:        http://localhost:8000"
	@echo "API docs:   http://localhost:8000/docs"
	@echo "API metrics: http://localhost:8000/metrics"

.PHONY: down
down: ## Stop the stack, keeping volumes
	$(COMPOSE) down

.PHONY: clean
clean: ## Stop the stack and delete volumes (destroys data)
	$(COMPOSE) down -v

.PHONY: logs
logs: ## Tail logs from all services
	$(COMPOSE) logs -f

.PHONY: ps
ps: ## Show service status
	$(COMPOSE) ps

.PHONY: scale
scale: ## Run 3 probe workers to demonstrate horizontal scaling
	$(COMPOSE) up -d --scale worker=3

# ---------------------------------------------------------------------------
# Database
# ---------------------------------------------------------------------------

.PHONY: migrate
migrate: ## Apply migrations inside the api container
	$(COMPOSE) exec api alembic upgrade head

.PHONY: revision
revision: ## Autogenerate a migration: make revision m="add table"
	$(COMPOSE) exec api alembic revision --autogenerate -m "$(m)"

.PHONY: psql
psql: ## Open a psql shell
	$(COMPOSE) exec postgres psql -U sentinel -d sentinel

# ---------------------------------------------------------------------------
# Demo
# ---------------------------------------------------------------------------

.PHONY: seed
seed: ## Create a few example monitors against the running API
	./scripts/seed.sh

.PHONY: smoke
smoke: ## Verify the running stack end to end
	./scripts/smoke.sh
