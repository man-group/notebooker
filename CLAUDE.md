# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Notebooker is a production system for executing and scheduling Jupyter Notebooks as parametrized reports. It converts notebooks (stored as .py files via Jupytext) into web-based reports with results stored in MongoDB.

## Common Commands

### Python Development
```bash
# Install in development mode
pip install -e ".[test]"

# Install kernel for notebook execution
python -m ipykernel install --user --name=notebooker_kernel

# Run tests (requires MongoDB)
pytest -svvvvv --junitxml=test-results/junit.xml

# Code quality
flake8 notebooker tests
black --check -l 120 notebooker tests

# Build docs
pip install -e ".[docs]"
sphinx-build -b html docs/ build/sphinx/html
```

### JavaScript Development
```bash
cd notebooker/web/static/

yarn install --frozen-lockfile
yarn run lint      # ESLint
yarn run format    # Prettier
yarn run bundle    # Browserify scheduler.js
yarn test          # Jest
```

### Quick Demo
```bash
cd docker && docker-compose up
# Access at http://localhost:8080/
```

## Architecture

### Core Components

- **`notebooker/execute_notebook.py`** - Notebook execution engine using Papermill
- **`notebooker/_entrypoints.py`** - Click-based CLI (`notebooker-cli`)
- **`notebooker/web/app.py`** - Flask webapp with Gevent WSGI server
- **`notebooker/serialization/`** - Storage backend interfaces
- **`notebooker/serializers/`** - MongoDB implementation (PyMongoResultSerializer)

### Entry Points
- `notebooker-cli` - Main CLI with subcommands: `start-webapp`, `execute-notebook`, `cleanup-old-reports`
- `notebooker_execute` - Docker-compatible entrypoint
- `notebooker_template_sanity_check` - Template validation
- `notebooker_template_regression_test` - Regression testing

### Execution Flow
1. Templates stored as .py files (Jupytext format) in git
2. Converted to .ipynb via `generate_ipynb_from_py()`
3. Executed with Papermill using parameters
4. Output converted to HTML/PDF via nbconvert
5. Results stored in MongoDB with GridFS for large files

### Web App Routes
- `/run_report/` - Execute notebooks
- `/results/` - Serve completed reports
- `/pending/` - Monitor running reports
- `/scheduler/` - Schedule management

### Template Parameters
Define parameters in templates using the Jupytext tag format:
```python
# + {"tags": ["parameters"]}
param_name = "default_value"
```

## Key Configuration

- `NOTEBOOK_KERNEL_NAME` - Kernel for execution (default: `notebooker_kernel`)
- `PY_TEMPLATE_BASE_DIR` - Git repo containing templates
- `SERIALIZER_CLS` / `SERIALIZER_CONFIG` - Storage backend config
- `NOTEBOOKER_DISABLE_GIT` - Skip git pulls during execution
- `SCHEDULER_MANAGEMENT_ONLY` - Webapp manages jobs but doesn't execute them (use with standalone scheduler)

## Standalone Scheduler

The scheduler can run as a standalone process instead of a background thread in the webapp:

```bash
# Webapp (manages jobs, doesn't execute)
notebooker-cli start-webapp --scheduler-management-only

# Standalone scheduler (executes jobs)
notebooker-cli start-scheduler
```

Key files: `scheduler_core.py` (shared infrastructure), `standalone_scheduler.py` (standalone process), `global_config.py` (shared GLOBAL_CONFIG state)

The standalone scheduler exposes `GET /healthz` on port 11829 by default (set `--liveness-port 0` to disable).

## Version Consistency

When bumping versions, update all of:
- `notebooker/version.py`
- `CHANGELOG.md`
- `docs/conf.py`
- `notebooker/web/static/package.json`

## Testing

Tests require MongoDB. The test suite uses pytest-server-fixtures for MongoDB test servers. Test directories:
- `tests/unit/` - Unit tests
- `tests/integration/` - Integration tests
- `tests/regression/` - Regression tests
- `tests/sanity/` - Sanity checks
