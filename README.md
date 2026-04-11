# WhatsApp Analyzer

[![CI](https://github.com/asaf-kali/whatsapp-analyzer/actions/workflows/ci.yml/badge.svg)](https://github.com/asaf-kali/whatsapp-analyzer/actions/workflows/ci.yml)
[![Ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff)
[![Type checked: mypy](https://img.shields.io/badge/type%20check-mypy-22aa11)](http://mypy-lang.org/)

A local web dashboard for analyzing WhatsApp chat history, built directly on decrypted SQLite database files.

**All processing is local. No message data is sent to any external service.**

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

### Pages

**Summary** — Global activity heatmap across all chats, key stats (total messages, active days, busiest day). Click any day for a detailed message view.

**Messages** — Browse and search all messages across all chats. Filter by message content, date range, group/chat, and sender. All filters are server-side with pagination.

**Network** — Global cross-chat contact graph. Nodes = contacts; edges = number of shared groups. Community detection with color-coded clusters.

**Per-chat pages** (Overview, Timeline, Participants, Words & Emoji, Media, Messages, Network) — Deep analysis of a single chat.

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
git clone https://github.com/asaf-kali/whatsapp-analyzer
cd whatsapp-analyzer
just install

# 2. Place your decrypted database files in data/  (gitignored)
mkdir -p data
cp /path/to/msgstore.db data/
cp /path/to/wa.db data/      # optional — enables contact name resolution

# 3. Build the frontend and start the server
just frontend-build
just run --msgstore data/msgstore.db --wadb data/wa.db

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

---

## Architecture

```
msgstore.db ──┐
              ├──▶ DBConnection ──▶ DataLoader ──▶ pd.DataFrame (cached)
wa.db ────────┘                                          │
                                                         ▼
                                               Analysis functions
                                            (timeline, participants, …)
                                                         │
                                                         ▼
                                               FastAPI routes ──▶ JSON
                                                         │
                                                         ▼
                                          React + TanStack Query (browser)
```

Four strict layers. `PYTHONPATH=app` so imports are e.g. `from db.loaders import DataLoader`.

| Layer | Path | Responsibility |
|-------|------|----------------|
| DB | `app/db/` | Read-only SQLite access; `DataLoader` resolves contacts, normalises timestamps to local TZ |
| Models | `app/models/` | Pydantic types for config, message metadata, chat summaries; `AnalysisConfig.cache_key()` drives LRU cache |
| Analysis | `app/analysis/` | Pure functions: `(pd.DataFrame, AnalysisConfig) → pd.DataFrame`, registered with `@analysis(...)` |
| API | `app/api/` | FastAPI routes; `deps.get_df()` loads and caches DataFrames |

### Key API endpoints

| Endpoint | Description |
|----------|-------------|
| `GET /api/messages` | Global messages — search, date range, `chat_ids[]`, `sender_ids[]`, pagination |
| `GET /api/senders` | All unique senders (for filter UI population) |
| `GET /api/chats/{id}/messages` | Per-chat messages — search, date range, sender filter, pagination |
| `GET /api/network` | Global cross-chat contact network |
| `GET /api/search` | Full-text message search (quick, no pagination) |

---

## Privacy

- **No network calls.** The server binds to `127.0.0.1` by default and never makes outbound requests.
- **No telemetry, no analytics, no cloud.** This tool reads files from your disk and renders charts in your browser. Nothing leaves your machine.
- The `data/` directory (where your `.db` files live) is in `.gitignore` and will never be committed.
