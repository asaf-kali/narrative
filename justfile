# Variables

PYTHON_TEST_COMMAND := "pytest"
OPEN_FILE_COMMAND := "wslview"
DEL_COMMAND := "gio trash"
RUN := "uv run"

# Install

install-run:
    uv sync --no-default-groups

install-test:
    uv sync --no-default-groups --group test

install-all:
    uv sync --all-groups

install-dev: install-all
    {{ RUN }} pre-commit install

install: install-dev lint cover-base

# UV

lock:
    uv lock

lock-upgrade:
    uv lock --upgrade

lock-check:
    uv lock --check

# Test

test *args:
    {{ RUN }} python -m {{ PYTHON_TEST_COMMAND }} {{ args }}

cover-base *args:
    {{ RUN }} coverage run -m {{ PYTHON_TEST_COMMAND }} {{ args }}
    {{ RUN }} coverage report

cover-xml: cover-base
    {{ RUN }} coverage xml

cover-html: cover-base
    {{ RUN }} coverage html

cover-percentage:
    {{ RUN }} coverage report --precision 3 | grep TOTAL | awk '{print $4}' | sed 's/%//'

cover: cover-html
    {{ OPEN_FILE_COMMAND }} htmlcov/index.html &
    {{ DEL_COMMAND }} .coverage*

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
