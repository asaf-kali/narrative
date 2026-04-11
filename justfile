# Variables

OPEN_FILE_COMMAND := "wslview"
RUN := "uv run"
NPM := "npm --prefix frontend"

# Install

install: install-dev lint

install-run:
    uv sync --no-default-groups

install-lint:
    uv sync --group lint

install-all:
    uv sync --all-groups

install-dev: install-all frontend-install
    {{ RUN }} pre-commit install

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

# Backend

backend-dev *args:
    PYTHONPATH=app {{ RUN }} python app/main.py --reload {{ args }}

run *args:
    PYTHONPATH=app {{ RUN }} python app/main.py {{ args }}

run-dev *args:
    just backend-dev {{ args }} & just frontend-dev

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

# Misc

decrypt-backup key:
    cd etc && wadecrypt {{ key }} msgstore.db.crypt15
    cd etc && wadecrypt {{ key }} wa.db.crypt15
