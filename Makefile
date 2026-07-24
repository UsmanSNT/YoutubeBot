.PHONY: help init init-dev run tests test check format lint lint-all mypy deps-check clean docker-start docker-build docker-logs docker-status docker-stop docker-clean nas-init nas-bootstrap nas-status nas-logs nas-restart nas-stop nas-push nas-backup nas-clean nas-info
.DEFAULT_GOAL := help

# Default Python command using uv
PY := uv run python
PYTEST := uv run pytest
MYPY := uv run mypy
RUFF := uv run ruff
FLAKE8 := uv run flake8

# Help command
help: ## Show this help message
	@echo 'Usage: make [target]'
	@echo ''
	@echo 'Targets:'
	@awk 'BEGIN {FS = ":.*?## "} /^[a-zA-Z_-]+:.*?## / {printf "\033[36m%-15s\033[0m %s\n", $$1, $$2}' $(MAKEFILE_LIST) | sort

# Setup commands
init: ## Initialize project after cloning (install dependencies)
	@echo "Initializing project..."
	@echo "Checking uv installation..."
	@which uv > /dev/null || (echo "Error: uv is not installed. Please install uv first: https://github.com/astral-sh/uv" && exit 1)
	@echo "Installing project dependencies..."
	@uv pip install -e .
	@echo "Creating .env file from template..."
	@if [ ! -f .env ]; then cp .env.example .env && echo ".env file created. Please edit it with your tokens."; else echo ".env file already exists."; fi
	@echo "Project initialized! Edit .env file and run 'make run' to start."

init-dev: ## Initialize development environment (install dev dependencies)
	@echo "Initializing development environment..."
	@echo "Checking uv installation..."
	@which uv > /dev/null || (echo "Error: uv is not installed. Please install uv first: https://github.com/astral-sh/uv" && exit 1)
	@echo "Installing project with dev dependencies..."
	@uv pip install -e ".[dev]"
	@echo "Creating .env file from template..."
	@if [ ! -f .env ]; then cp .env.example .env && echo ".env file created. Please edit it with your tokens."; else echo ".env file already exists."; fi
	@echo "Development environment initialized! Edit .env file and run 'make run' to start."

# Run the bot
run: ## Run the bot
	$(PY) run.py

# Run all tests with coverage
tests: ## Run all tests with coverage and generate HTML report
	$(PYTEST) --cov=bot --cov-report=term-missing --cov-report=html

# Run a specific test (usage: make test test_file.py::test_function)
test: ## Run specific test with coverage report (e.g., make test test_config.py or test_config.py::test_function)
	@if [ -z "$(filter-out test,$@)" ]; then \
		echo "Usage: make test <test_file.py::test_function_name>"; \
	else \
		$(PYTEST) tests/$(filter-out test,$@) --cov=bot --cov-report=term-missing --cov-report=html; \
	fi

# Format code
format: ## Format code with ruff
	$(RUFF) format .

# Lint code with ruff
lint: ## Lint code with ruff
	$(RUFF) check .

# Lint code with wemake-python-styleguide
lint-wps: ## Lint code with wemake-python-styleguide
	$(FLAKE8) . --select=WPS

# Lint code with all linters
lint-all: format lint lint-wps ## Run all linting (format, ruff lint, wemake-python-styleguide)
	@echo "All linting completed"

# Type check
mypy: ## Run type checking with mypy
	$(MYPY) .

# Check dependencies installation
deps-check: ## Check if all dependencies are properly installed
	@echo "Checking uv installation..."
	@which uv > /dev/null || (echo "Error: uv is not installed" && exit 1)
	@echo "Checking Python environment..."
	@$(PY) --version
	@echo "Checking project dependencies..."
	@uv pip check || echo "Warning: Some dependencies may have issues"
	@echo "Dependencies check completed"

# Clean temporary files
clean: ## Clean temporary files and cache
	@echo "Cleaning temporary files..."
	@find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	@find . -type f -name "*.pyc" -delete 2>/dev/null || true
	@find . -type f -name "*.pyo" -delete 2>/dev/null || true
	@find . -type d -name "*.egg-info" -exec rm -rf {} + 2>/dev/null || true
	@rm -rf .pytest_cache/ .coverage htmlcov/ .mypy_cache/ .ruff_cache/ 2>/dev/null || true
	@rm -rf data/temp/* 2>/dev/null || true
	@echo "Cleanup completed"

# Run all checks (format, lint, type check)
check: format lint mypy ## Run all checks (format, lint, type check)

# Docker targets
docker-start: ## Start Docker environment
	@echo "Starting Docker environment..."
	@if [ ! -f .env ]; then \
		echo "Creating .env from .env.example template..."; \
		cp .env.example .env; \
		echo "Please edit .env with your actual tokens"; \
	fi
	@docker compose up -d

docker-build: ## Build Docker image
	@echo "Building Docker image..."
	@docker compose build

docker-logs: ## Show Docker container logs
	@docker compose logs -f videograbber-bot

docker-status: ## Show Docker containers status
	@docker compose ps

docker-stop: ## Stop Docker containers
	@echo "Stopping Docker containers..."
	@docker compose down

docker-clean: docker-stop ## Stop containers and clean up
	@echo "Cleaning up Docker resources..."
	@docker system prune -f

# NAS deploy helpers
nas-init: ## Initialize NAS deployment (check requirements, setup SSH, bootstrap)
	@echo "Initializing NAS deployment..."
	@echo "1. Checking SSH configuration..."
	@if ! ssh nas 'echo "SSH connection OK"' 2>/dev/null; then \
		echo "SSH connection failed. Please configure SSH access first:"; \
		echo "Add to ~/.ssh/config:"; \
		echo "Host nas"; \
		echo "    HostName your_nas_hostname"; \
		echo "    User your_nas_user"; \
		echo "    IdentityFile ~/.ssh/id_ed25519"; \
		echo "Also create .nas_deploy.env from .nas_deploy.env.example"; \
		exit 1; \
	fi
	@echo "2. Running bootstrap setup..."
	@bash scripts/nas_bootstrap.sh
	@echo "3. NAS deployment initialization complete!"

nas-bootstrap: ## Bootstrap NAS autodeploy (creates bare repo, installs hook, sets remote)
	@bash scripts/nas_bootstrap.sh

nas-push: ## Push main branch to NAS (deploy)
	@git push nas main:main || git push_nas

nas-status: ## Show NAS service status (docker compose ps)
	@bash scripts/nas_exec.sh -- '/usr/local/bin/docker compose ps'

nas-logs: ## Tail NAS bot logs
	@bash scripts/nas_exec.sh -- '/usr/local/bin/docker compose logs -f --tail=200 videograbber-bot'

nas-restart: ## Restart NAS bot service
	@bash scripts/nas_exec.sh -- '/usr/local/bin/docker compose restart videograbber-bot'

nas-stop: ## Stop NAS bot service
	@bash scripts/nas_exec.sh -- '/usr/local/bin/docker compose stop videograbber-bot'

nas-backup: ## Create backup of NAS deployment
	@echo "Creating backup of NAS deployment..."
	@bash scripts/nas_exec.sh -- 'tar -czf /tmp/videograbber-backup-$(date +%Y%m%d-%H%M%S).tar.gz .'
	@echo "Downloading backup to local machine..."
	@scp nas:/tmp/videograbber-backup-*.tar.gz ./backups/ 2>/dev/null || mkdir -p backups && scp nas:/tmp/videograbber-backup-*.tar.gz ./backups/
	@bash scripts/nas_exec.sh -- 'rm -f /tmp/videograbber-backup-*.tar.gz'
	@echo "Backup completed and stored in ./backups/"

nas-clean: ## Clean old Docker images and containers on NAS
	@echo "Cleaning up Docker resources on NAS..."
	@bash scripts/nas_exec.sh -- '/usr/local/bin/docker image prune -f'
	@bash scripts/nas_exec.sh -- '/usr/local/bin/docker container prune -f'
	@bash scripts/nas_exec.sh -- '/usr/local/bin/docker system prune -f'
	@echo "Cleanup completed"

nas-info: ## Show NAS deployment information
	@echo "=== NAS Deployment Information ==="
	@bash scripts/nas_exec.sh -- 'pwd && ls -la'
	@echo ""
	@echo "=== Docker Status ==="
	@bash scripts/nas_exec.sh -- '/usr/local/bin/docker compose ps'
	@echo ""
	@echo "=== Git Remote ==="
	@git remote -v | grep nas || echo "NAS remote not configured"
