.PHONY: help install install-dev lint format type-check test clean pre-commit-install

help:  ## Show this help message
	@echo 'Usage: make [target]'
	@echo ''
	@echo 'Targets:'
	@awk 'BEGIN {FS = ":.*?## "} /^[a-zA-Z_-]+:.*?## / {printf "  %-20s %s\n", $$1, $$2}' $(MAKEFILE_LIST)

install:  ## Install production dependencies
	cd backend && pip install -r requirements.txt

install-dev:  ## Install development dependencies
	cd backend && pip install -r requirements.txt -r requirements-dev.txt

lint:  ## Run linting (ruff)
	cd backend && ruff check .

format:  ## Format code (black + ruff)
	cd backend && black .
	cd backend && ruff check --fix .

type-check:  ## Run type checking (mypy)
	cd backend && mypy .

test:  ## Run tests
	cd backend && python manage.py test

clean:  ## Clean cache and temporary files
	find . -type f -name "*.pyc" -delete
	find . -type d -name "__pycache__" -delete
	find . -type d -name "*.egg-info" -exec rm -rf {} +

pre-commit-install:  ## Install pre-commit hooks
	pre-commit install

check-all: lint type-check test  ## Run all checks