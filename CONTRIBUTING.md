# Contributing to VideoGrabberBot

Thank you for your interest in contributing to VideoGrabberBot! This document provides guidelines and instructions for developers.

## Development Setup

### Prerequisites

- Python 3.13+
- [uv](https://github.com/astral-sh/uv) - Python package installer and environment manager
- Git

### Quick Start

1. **Fork and clone the repository**:
   ```bash
   git clone https://github.com/YOUR_USERNAME/VideoGrabberBot.git
   cd VideoGrabberBot
   ```

2. **Initialize development environment**:
   ```bash
   make init-dev
   ```
   This will:
   - Install all dependencies including dev tools
   - Create `.env` file from template
   - Set up the project for development

3. **Configure environment**:
   Edit `.env` file with your bot tokens:
   ```
   TELEGRAM_TOKEN=your_telegram_bot_token
   ADMIN_USER_ID=your_telegram_user_id
   ```

4. **Verify setup**:
   ```bash
   make deps-check
   make tests
   ```

## Development Workflow

### Available Commands

All development tasks are available through Makefile. Run `make help` to see all available commands:

```bash
# Project initialization
make init          # Initialize project after cloning
make init-dev      # Initialize with dev dependencies

# Running
make run           # Run the bot

# Testing  
make tests         # Run all tests with coverage
make test          # Run specific test (e.g., make test test_config.py)

# Code quality
make format        # Format code with ruff
make lint          # Lint code with ruff  
make lint-wps      # Lint with wemake-python-styleguide
make lint-all      # Run all linting tools
make mypy          # Type checking
make check         # Run all checks (format, lint, type check)

# Docker development
make docker-start  # Start Docker environment
make docker-build  # Build Docker image
make docker-logs   # View logs
make docker-status # Check status
make docker-stop   # Stop containers
make docker-clean  # Clean up

# Utilities
make clean         # Clean temporary files
make deps-check    # Check dependencies
```

### Code Quality Standards

This project maintains high code quality standards using multiple tools:

- **Type Checking**: Static type checking with mypy
- **Linting**: 
  - Primary linter: Ruff for fast checking and auto-fixes
  - Secondary linter: wemake-python-styleguide for strict enforcement of best practices
- **Formatting**: Automatic code formatting with Ruff
- **Testing**: Comprehensive test suite with pytest
  - Minimum 85% coverage requirement
  - Parallel execution for unit and security tests
  - Sequential execution for integration tests (prevents race conditions)
  - All configuration centralized in `pyproject.toml`

### Development Guidelines

1. **Before making changes**:
   ```bash
   make check  # Ensure code quality
   make tests  # Run all tests
   ```

2. **Creating Tests**: 
   - When creating tests for existing code, never modify the code itself
   - New features should include comprehensive tests
   - Maintain minimum test coverage of 85%

3. **Code Style**:
   - **Imports**: Standard lib → Third-party → Local (alphabetical within groups)
   - **Types**: Use type annotations for all functions and variables
   - **Naming**: snake_case for variables/functions, UPPER_CASE for constants
   - **Language**: Always use English for ALL code, comments, and docstrings
   - **Docstrings**: Google style docstrings for all modules, classes, and functions

4. **Error handling**: Use try/except with specific exceptions, log errors with loguru

5. **Async**: Use async/await for I/O bound operations (DB, network)

### Testing

```bash
# Run all tests
make tests

# Run specific test file
make test test_config.py

# Run specific test function
make test test_config.py::test_function_name

# Run tests with coverage report
make tests  # Automatically includes coverage
```

The test suite is organized into three categories:
- `tests/unit/` - Unit tests that mirror the `bot/` directory structure
- `tests/integration/` - Integration tests for complete workflows
- `tests/security/` - Security and authorization tests

All tests run in parallel except integration tests, which run sequentially to avoid race conditions with shared state.

### Security Testing

```bash
# Run security tests specifically
make test tests/security/

# Run all security-related tests
make test tests/security/ tests/unit/handlers/test_download.py
```

**Security Testing Guidelines:**
- All new handlers must include both authorized and unauthorized test cases
- Use real database in security tests, not mocks, for accurate authorization validation
- Test for authorization bypass attempts, especially in callback handlers
- Each security test should verify both success and failure scenarios
- Security vulnerabilities should be documented in commit messages

### Docker Development

The project includes simple Docker support:

```bash
# Docker environment
make docker-start   # Start Docker container
make docker-logs    # View logs
make docker-status  # Check container status

# Cleanup
make docker-stop    # Stop container
make docker-clean   # Clean up Docker resources
```

## Project Structure

### Module Dependencies
```
bot/
├── handlers/ (depends on services/, utils/)
├── services/ (depends on utils/)
├── utils/ (no internal dependencies)
└── telegram_api/ (isolated)
```

```
VideoGrabberBot/
├── bot/                    # Main bot code
│   ├── handlers/           # Telegram message and callback handlers with authorization
│   ├── services/           # Core business logic (downloader, queue, formats, storage)
│   ├── telegram_api/       # Telegram API client
│   └── utils/              # Database operations, logging, configuration utilities
├── tests/                  # Test suite
│   ├── integration/        # Integration tests (workflow and error handling)
│   ├── security/           # Security and authorization tests
│   └── unit/               # Unit tests (mirrors bot/ structure)
│       ├── handlers/       # Tests for bot/handlers/
│       ├── services/       # Tests for bot/services/
│       ├── telegram_api/   # Tests for bot/telegram_api/
│       └── utils/          # Tests for bot/utils/
├── data/                   # Database and temp files
├── Dockerfile              # Container image definition
├── docker-compose.yml      # Container orchestration
├── .dockerignore           # Files to exclude from Docker context
├── .env.example            # Environment variables template
├── .flake8                 # wemake-python-styleguide configuration
├── pyproject.toml          # Project configuration and dependencies
├── Makefile                # Development workflow commands
├── CLAUDE.md               # Development guidelines
└── CONTRIBUTING.md         # This file
```

## Submitting Changes

1. **Create a feature branch**:
   ```bash
   git checkout -b feature/your-feature-name
   ```

2. **Make your changes following the guidelines above**

3. **Ensure code quality**:
   ```bash
   make check   # Format, lint, and type check
   make tests   # Run all tests
   ```

4. **Commit your changes**:
   ```bash
   git add .
   git commit -m "feat: add your feature description"
   ```

5. **Push and create a Pull Request**:
   ```bash
   git push origin feature/your-feature-name
   ```

### Commit Message Format

Follow conventional commits format:
- `feat:` - New features
- `fix:` - Bug fixes
- `docs:` - Documentation changes
- `style:` - Code style changes (formatting, etc.)
- `refactor:` - Code refactoring
- `test:` - Adding or updating tests
- `chore:` - Other changes (dependencies, build, etc.)

## Getting Help

- Check existing [Issues](https://github.com/AABur/VideoGrabberBot/issues)
- Create a new issue for bugs or feature requests
- For development questions, feel free to open a discussion

## Code of Conduct

This is a personal educational project. Please be respectful and constructive in all interactions.

Thank you for contributing! 🚀