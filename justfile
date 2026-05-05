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

backend *args:
    PYTHONPATH=app {{ RUN }} python app/main.py serve {{ args }}

backend-dev *args:
    just backend {{ args }} --reload

# Run

run *args: frontend-build
    just backend {{ args }}

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

index *args:
    PYTHONPATH=app {{ RUN }} python app/main.py index {{ args }}

decrypt key:
    cd data && wadecrypt {{ key }} msgstore.db.crypt15 msgstore.db
    -cd data && wadecrypt {{ key }} wa.db.crypt15 wa.db
