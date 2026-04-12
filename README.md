# Narrative

[![CI](https://github.com/asaf-kali/narrative/actions/workflows/ci.yml/badge.svg)](https://github.com/asaf-kali/narrative/actions/workflows/ci.yml)
[![Ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff)
[![Type checked: mypy](https://img.shields.io/badge/type%20check-mypy-22aa11)](http://mypy-lang.org/)

A local analytics dashboard for exploring the narrative hidden in your WhatsApp chat history. Reads decrypted SQLite databases directly, unlocking insights text exports cannot provide.

- **All processing is local** — No network calls, no telemetry, no cloud
- **No message data is sent anywhere** — Server binds to `127.0.0.1` only
- **Database files never committed** — `data/` directory is gitignored

---

## What It Does

Most WhatsApp analyzers work from text exports (`.txt` files). This tool reads the actual encrypted-then-decrypted SQLite databases (`msgstore.db` + `wa.db`) that WhatsApp stores on your Android device — giving access to far richer data:

| Feature | Text export | This tool |
|---------|------------|-----------|
| Message text | ✅ | ✅ |
| Timestamps | Approximate | Exact (millisecond) |
| Media metadata | ❌ | ✅ |
| Reactions | ❌ | ✅ |
| Voice note duration | ❌ | ✅ |
| Call logs | ❌ | ✅ |
| Reply chains | ❌ | ✅ |
| Deleted messages | ❌ | ✅ |

---

## Getting the Database Files

Your WhatsApp messages are stored in encrypted SQLite databases on your Android device. To use this tool:

1. Back up your WhatsApp data from your Android device (via WhatsApp Settings → Chats → Chat backup).
2. Locate `msgstore.db.crypt15` (or similar) on your device storage at `Internal Storage/WhatsApp/Databases/`.
3. Decrypt using a tool such as [wa-crypt-tools](https://github.com/ElDavoo/wa-crypt-tools) with your device's backup key.
4. The decrypted `msgstore.db` and optionally `wa.db` (for contact names) are your inputs.

```bash
# Decrypt backup files into data/
just decrypt-backup <key>
```

> Your decrypted `.db` files contain all your messages. Keep them secure and never share them.

---

## Prerequisites

- [uv](https://docs.astral.sh/uv/) `>= 0.9`
- [just](https://github.com/casey/just) command runner
- Node.js 20+ (only needed for frontend development)

---

## Setup

```bash
# 1. Clone and install dependencies
git clone https://github.com/asaf-kali/narrative
cd narrative
just install

# 2. Place your decrypted database files in data/  (gitignored)
mkdir -p data
cp /path/to/msgstore.db data/
cp /path/to/wa.db data/      # optional — enables contact name resolution

# 3. Start the server (builds frontend automatically)
just run

# Opens at http://127.0.0.1:8050
```

---

## Development

```bash
# Terminal 1 — backend with auto-reload
just run-dev --msgstore data/msgstore.db

# Terminal 2 — Vite dev server (proxies /api → :8050)
just frontend-dev
# Open http://localhost:5173
```

Other useful commands:

```bash
just lint          # format + ruff fix + pre-commit
just check-ruff    # ruff format + lint check (CI)
just check-mypy    # mypy type check (CI)
just frontend-build  # build React app into frontend/dist/
```
