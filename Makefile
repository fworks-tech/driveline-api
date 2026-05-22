PYTHON = venv/Scripts/python
PIP    = venv/Scripts/pip
PYTEST = venv/Scripts/pytest
MANAGE = $(PYTHON) manage.py

.PHONY: help install dev migrate makemigrations test test-cov lint shell \
        docker-up docker-down docker-build docker-logs resetdb

help:
	@echo "Available commands:"
	@echo "  make install       Create venv and install dependencies"
	@echo "  make dev           Start Django dev server on port 8000"
	@echo "  make migrate       Apply database migrations"
	@echo "  make makemigrations  Create new migrations"
	@echo "  make test          Run test suite"
	@echo "  make test-cov      Run tests with coverage report"
	@echo "  make lint          Run black + isort checks"
	@echo "  make shell         Open Django shell"
	@echo "  make docker-up     Start all services via Docker Compose"
	@echo "  make docker-down   Stop all Docker Compose services"
	@echo "  make docker-build  Rebuild Docker images"
	@echo "  make docker-logs   Tail Docker Compose logs"
	@echo "  make resetdb       Drop and recreate the local database"

install:
	python -m venv venv
	$(PIP) install -r requirements.txt

dev:
	$(MANAGE) runserver 8000

migrate:
	$(MANAGE) migrate

makemigrations:
	$(MANAGE) makemigrations

test:
	$(PYTEST) trips/tests/ -v

test-cov:
	$(PYTEST) trips/tests/ -v --cov=trips --cov-report=html --cov-report=term-missing

lint:
	venv/Scripts/black --check .
	venv/Scripts/isort --check-only .

shell:
	$(MANAGE) shell

docker-up:
	docker compose up

docker-down:
	docker compose down

docker-build:
	docker compose up --build

docker-logs:
	docker compose logs -f
