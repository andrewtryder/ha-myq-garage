# Agent Instructions for Home Assistant MyQ Garage Integration

This file provides context and instructions for AI agents (like Jules, Cursor, Antigravity) working on this repository.

## General Context
This repository contains a Home Assistant custom component integration for "MyQ Garage". It interacts with a custom REST API using JSON payloads.
The core integration logic is located in `custom_components/myq_garage/`.

## File Structure
- `custom_components/myq_garage/`: The main integration code.
  - `client.py`: Handles communication with the MyQ Garage custom API.
  - `cover.py`: Home Assistant cover entity platform.
  - `config_flow.py`: Handles the UI configuration setup for Home Assistant.
  - `coordinator.py`: Data update coordinator handling the polling.
- `tests/`: Unit tests using `pytest` and `pytest-homeassistant-custom-component`.
- `pyproject.toml`: Configuration for `ruff` and `pytest`.

## Release and Commit Conventions
**CRITICAL:** This project uses `release-please` for automated changelog generation and version bumping.
You **must** follow the [Conventional Commits](https://www.conventionalcommits.org/en/v1.0.0/) specification for all commit messages.

*   `feat: <description>`: For new features (bumps minor version).
*   `fix: <description>`: For bug fixes (bumps patch version).
*   `docs: <description>`, `chore: <description>`, `test: <description>`, `refactor: <description>`: For non-code changes (does not bump version).
*   Add `!` after the type/scope for breaking changes (e.g., `feat!: <description>`), which will bump the major version.

## Local Development and Tooling

### Python Environment
To test changes, you can set up a local virtual environment:
```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/pip install -r requirements_test.txt
```

### Formatting and Linting (Ruff)
This project enforces code styles and format rules using `ruff`. Run these checks locally before committing changes:
```bash
# Run styling checks
.venv/bin/ruff check custom_components/ tests/

# Auto-format files
.venv/bin/ruff format custom_components/ tests/
```

### Pre-commit Hooks
The project uses `pre-commit`. Always ensure you run pre-commit or ensure hooks pass:
```bash
.venv/bin/pre-commit run --all-files
```

### Testing (Pytest)
Tests are written with `pytest`. Run the test suite to verify your changes and check coverage:
```bash
PYTHONPATH=. .venv/bin/pytest --cov=custom_components/myq_garage --cov-report=term-missing
```

### Hassfest Validation
When modifying the structure of the custom component, validate it using `hassfest` via Docker:
```bash
docker run --rm -v "$(pwd):/github/workspace" ghcr.io/home-assistant/hassfest
```
