# TradingOS Makefile

.PHONY: help install test lint typecheck format build run clean

# Default target
help:
	@echo "TradingOS Development Commands"
	@echo ""
	@echo "Setup:"
	@echo "  install         Install package in development mode"
	@echo "  install-dev     Install with all dev dependencies"
	@echo ""
	@echo "Testing:"
	@echo "  test            Run all tests"
	@echo "  test-unit       Run unit tests only"
	@echo "  test-integration Run integration tests only"
	@echo "  test-cov        Run tests with coverage"
	@echo ""
	@echo "Code Quality:"
	@echo "  lint            Run ruff linter"
	@echo "  format          Format code with ruff"
	@echo "  typecheck       Run mypy type checker"
	@echo "  check           Run all checks (lint, typecheck, test)"
	@echo ""
	@echo "Building:"
	@echo "  build           Build wheel package"
	@echo "  build-docker    Build Docker image"
	@echo ""
	@echo "Running:"
	@echo "  run             Start TradingOS (market hours)"
	@echo "  run-after-hours Start TradingOS (after hours)"
	@echo "  run-health      Start health server only"
	@echo "  shell           Start interactive shell"
	@echo ""
	@echo "Database:"
	@echo "  migrate         Run database migrations"
	@echo ""
	@echo "Maintenance:"
	@echo "  clean           Clean build artifacts"

# Installation
install:
	pip install -e code

install-dev:
	pip install -e "code[dev]"

install-all:
	pip install -e "code[dev,vision,video,llm,training]"

# Testing
test:
	pytest tests/ -v --tb=short

test-unit:
	pytest tests/unit -v --tb=short

test-integration:
	pytest tests/integration -v --tb=short

test-cov:
	pytest tests/ -v --tb=short --cov=tradingos --cov-report=term-missing --cov-report=html

# Code Quality
lint:
	ruff check code/ tests/

format:
	ruff format code/ tests/

typecheck:
	mypy code/tradingos --ignore-missing-imports

check: lint typecheck test-unit

# Building
build:
	python -m build code --wheel --no-isolation

build-docker:
	docker build -t tradingos:latest -f Dockerfile .

# Running
run:
	python -m tradingos start --env development

run-after-hours:
	python -m tradingos after_hours --env development

run-health:
	python -m tradingos health --env development

run-prod:
	python -m tradingos start --env production

shell:
	python -m tradingos shell --env development

migrate:
	python -m tradingos migrate --env development

# Maintenance
clean:
	rm -rf build dist *.egg-info
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete
	rm -rf .pytest_cache .mypy_cache .ruff_cache htmlcov

# Development helpers
dev-setup: install-dev
	pre-commit install

pre-commit:
	pre-commit run --all-files

# Quick development cycle
dev: format lint typecheck test-unit

# Generate requirements.txt from pyproject.toml
requirements:
	pip freeze > requirements.txt

# Check for outdated dependencies
outdated:
	pip list --outdated

# Security audit
audit:
	pip-audit -r requirements.txt