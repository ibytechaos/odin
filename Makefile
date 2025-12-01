# Odin Framework Makefile
# ========================
# Usage: make <target>
#
# Run `make help` to see all available targets

.PHONY: help install install-all install-dev sync playwright clean test lint format typecheck run serve docker-build docker-up docker-down

# Default target
.DEFAULT_GOAL := help

# Colors for output
CYAN := \033[36m
GREEN := \033[32m
YELLOW := \033[33m
RESET := \033[0m

help: ## Show this help message
	@echo "$(CYAN)Odin Framework$(RESET) - Available targets:"
	@echo ""
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  $(GREEN)%-20s$(RESET) %s\n", $$1, $$2}'

# =============================================================================
# Installation
# =============================================================================

install: ## Install base dependencies
	uv sync

install-all: ## Install all dependencies including optional extras and browsers
	uv sync --all-extras
	@echo "$(YELLOW)Installing Playwright browsers...$(RESET)"
	uv run playwright install chromium
	@echo "$(GREEN)Installation complete!$(RESET)"

install-dev: ## Install development dependencies
	uv sync --extra dev
	uv run pre-commit install

sync: ## Sync dependencies (alias for uv sync)
	uv sync

playwright: ## Install Playwright browsers
	uv run playwright install chromium
	@echo "$(GREEN)Playwright browsers installed!$(RESET)"

playwright-deps: ## Install Playwright system dependencies (requires sudo)
	uv run playwright install-deps chromium

# =============================================================================
# Development
# =============================================================================

test: ## Run tests
	uv run pytest

test-unit: ## Run unit tests only
	uv run pytest -m unit

test-cov: ## Run tests with coverage report
	uv run pytest --cov=odin --cov-report=html

lint: ## Run linter (ruff check)
	uv run ruff check src/odin

lint-fix: ## Run linter and fix issues
	uv run ruff check src/odin --fix

format: ## Format code (ruff format)
	uv run ruff format src/odin

typecheck: ## Run type checker (mypy)
	uv run mypy src/odin

check: lint typecheck test ## Run all checks (lint, typecheck, test)

# =============================================================================
# Running
# =============================================================================

run: ## Run the demo application
	cd examples/demo && PYTHONPATH=../../src uv run python main.py

serve: ## Start Odin server (default: copilotkit protocol)
	uv run odin serve --protocol copilotkit --port 8000

serve-mcp: ## Start Odin MCP server
	uv run odin serve --protocol mcp --port 8001

serve-http: ## Start Odin HTTP/REST server
	uv run odin serve --protocol http --port 8000

repl: ## Start interactive REPL for testing tools
	uv run odin repl

# =============================================================================
# CLI Commands
# =============================================================================

list-tools: ## List all available tools
	uv run odin list --builtin

create-project: ## Create a new Odin project (usage: make create-project NAME=my-agent)
	uv run odin create $(NAME)

# =============================================================================
# Docker
# =============================================================================

docker-build: ## Build Docker image
	docker build -t odin:latest .

docker-up: ## Start services with docker-compose
	docker compose up -d

docker-down: ## Stop services
	docker compose down

docker-logs: ## View logs
	docker compose logs -f odin

docker-shell: ## Open shell in container
	docker compose exec odin /bin/sh

# =============================================================================
# Cleanup
# =============================================================================

clean: ## Clean build artifacts and caches
	rm -rf .pytest_cache
	rm -rf .mypy_cache
	rm -rf .ruff_cache
	rm -rf htmlcov
	rm -rf coverage.xml
	rm -rf .coverage
	rm -rf dist
	rm -rf build
	rm -rf *.egg-info
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true

clean-all: clean ## Clean everything including venv
	rm -rf .venv
