# whatsapp-analyzer

[![CI](https://github.com/asaf-kali/whatsapp-analyzer/actions/workflows/ci.yml/badge.svg)](https://github.com/asaf-kali/whatsapp-analyzer/actions/workflows/ci.yml)
[![Ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff)
[![Type checked: mypy](https://img.shields.io/badge/type%20check-mypy-22aa11)](http://mypy-lang.org/)

Personal template for python projects

## Local development

### Prerequisites

- [UV](https://docs.astral.sh/uv/) `>= 0.9`
- [just](https://github.com/casey/just) command runner

### Environment Setup

1. Clone the repository
2. Install dependencies: `just install`. This will:
    - Create a virtual environment
    - Install all dependencies
    - Install pre-commit hooks
    - Make sure linting and tests pass
3. Activate the virtual environment: `source .venv/bin/activate`.
4. That's it! You are ready to start developing.

### Workflow

1. Lint using `just lint`.
2. Run tests using `just test` / `just cover`.

## Deployment


## Other
