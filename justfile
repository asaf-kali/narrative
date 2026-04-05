# Variables
OPEN_FILE_COMMAND := "wslview"
RUN := "uv run"
NPM := "npm --prefix frontend"

# Install

install-run:
    uv sync --no-default-groups

install-dev:
    uv sync --group lint --group dev
    {{ RUN }} pre-commit install
    {{ NPM }} install

install: install-dev lint

# UV

lock:
    uv lock

lock-upgrade:
    uv lock --upgrade

lock-check:
    uv lock --check

# Frontend

frontend-install:
    {{ NPM }} install

frontend-build:
    {{ NPM }} run build

frontend-dev:
    {{ NPM }} run dev

# Run

run *args:
    PYTHONPATH=app {{ RUN }} python app/main.py {{ args }}

run-dev *args:
    PYTHONPATH=app {{ RUN }} python app/main.py --reload {{ args }}

# Lint

format:
    {{ RUN }} ruff format

check-ruff:
    {{ RUN }} ruff format --check
    {{ RUN }} ruff check

check-mypy:
    {{ RUN }} dmypy run .

lint: format
    {{ RUN }} ruff check --fix --unsafe-fixes
    {{ RUN }} pre-commit run --all-files
