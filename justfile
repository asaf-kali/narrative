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
    {{ RUN }} python -m narrative.main serve {{ args }}

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

check-ty:
    {{ RUN }} ty check .

lint: format
    {{ RUN }} ruff check --fix --unsafe-fixes
    {{ RUN }} pre-commit run --all-files

# Test

install-test:
    uv sync --group test

test *args:
    {{ RUN }} pytest {{ args }}

cover *args:
    {{ RUN }} pytest --cov=narrative --cov-report=term-missing --cov-fail-under=90 {{ args }}

# Misc

index *args:
    {{ RUN }} python -m narrative.main index {{ args }}

decrypt key:
    cd data && wadecrypt {{ key }} msgstore.db.crypt15 msgstore.db
    -cd data && wadecrypt {{ key }} wa.db.crypt15 wa.db

# Fetch encrypted WhatsApp DBs from connected Android device via adb.
# Override adb binary with ADB=..., base dir on device with WA_BASE_DIR=...
fetch-db dest="data":
    ./scripts/fetch_db.sh {{ dest }}

generate-mock out_dir="data/mock":
    uv run scripts/generate_mock_db.py {{ out_dir }}

# Compress raw DBs and contacts into a 7z archive.
backup:
    cd data && 7z a "Backup.7z" msgstore.db wa.db contacts.csv
