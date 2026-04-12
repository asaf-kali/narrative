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

Most WhatsApp analyzers work from text exports (`.txt` files). This tool reads the actual encrypted-then-decrypted SQLite databases (`msgstore.db` + `wa.db`) that WhatsApp stores on your Android device — giving access to far richer data. Visualize activity heatmaps, explore your contact network, analyze messaging patterns, and browse conversations with full metadata and reaction history.

---

## Getting the Database Files

> **Android only.** iOS stores WhatsApp data in a proprietary format not currently supported by this tool.

WhatsApp encrypts its local backup as `.crypt15` files. To decrypt them, you need a **64-digit encryption key** that you generate once in WhatsApp settings and must keep safe forever.

### 1. Generate your encryption key

1. In WhatsApp: **Settings → Chats → Chat Backup → End-to-end Encrypted Backup**
2. Tap **Turn On**, then choose **Use 64-digit encryption key** (not a password)
3. WhatsApp displays your 64-digit key — **copy it and store it in a safe place immediately**
4. Tap **Create** to enable encrypted backups

> ⚠️ **Do not lose your key.** It cannot be recovered from WhatsApp. Without it, your backup files are permanently unreadable. Store it in a password manager and never share it.

### 2. Back up and copy the files

1. Trigger a backup: **Settings → Chats → Chat Backup → Back Up Now**
2. Copy these files from your device to the `data/` directory (via USB cable, ADB, or a file manager app):
   - `Android/media/com.whatsapp/WhatsApp/Databases/msgstore.db.crypt15` — all messages
   - `Android/media/com.whatsapp/WhatsApp/Backups/wa.db.crypt15` *(optional — for contact names)*

### 3. Decrypt

```bash
just decrypt <your-64-digit-key>
```

> Your decrypted `.db` files contain all your messages in plain text. Keep them secure and never share them.

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

# 2. Copy encrypted backup files into data/ and decrypt (see "Getting the Database Files" above)
just decrypt <key>

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
