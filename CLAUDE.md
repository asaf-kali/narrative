# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

```bash
just lint                 # format + ruff fix + pre-commit
just run --msgstore data/msgstore.db --wadb data/wa.db   # start backend (serves built frontend)
just run-dev ...          # start backend with --reload
just frontend-dev         # start Vite dev server (localhost:5173, proxies /api to :8050)
just frontend-build       # build React app into frontend/dist/
```

mypy runs via `uv run dmypy run .` (daemon).

## Architecture

4 strict layers. `PYTHONPATH=app` so imports are e.g. `from db.loaders import DataLoader`.

**`app/db/`** — Read-only SQLite access. `DBConnection` is a context manager opening `msgstore.db` (required) and `wa.db` (optional). `DataLoader` resolves contact names, normalizes timestamps to local tz, and returns `pd.DataFrame`.

**`app/models/`** — Pydantic used for config and summaries only (never per-row). `AnalysisConfig.cache_key()` is the LRU cache key.

**`app/analysis/`** — Pure functions `(pd.DataFrame, AnalysisConfig) → pd.DataFrame`. Register with `@analysis(...)` decorator.

**`app/api/`** — FastAPI backend. `server.py` creates the app with lifespan (stores db paths in `app.state`). Routes in `routes/chats.py`, `routes/analysis.py`, and `routes/messages.py`. `deps.py` provides `get_df()` with LRU cache. In production, serves the built frontend from `frontend/dist/`. CORS allows `localhost:5173` for development.

**`frontend/`** — React 18 + TypeScript + Vite + Tailwind CSS + Recharts + TanStack Query + React Router v6. API client in `src/api/client.ts`. Top-level pages: Summary (`/`), Messages (`/messages`), Network (`/network`). Chat pages under `/chat/:chatId`: Overview, Timeline, Participants, Content (words/emoji), Media, Messages, Network.

## Dev workflow

1. `just run-dev --msgstore data/msgstore.db` — backend on :8050
2. In another terminal: `just frontend-dev` — Vite on :5173 (proxies /api to :8050)

For production: `just frontend-build` then `just run --msgstore data/msgstore.db`

## WhatsApp DB Schema Notes

The real schema varies by WhatsApp version. Queries in `app/db/queries/` are written defensively. Key `message_type` values:

| Value | Type |
|-------|------|
| 0 | Text |
| 1 | Image |
| 2 | Audio / Voice note |
| 3 | Video |
| 7 | System notification (filtered by default) |
| 9 | Document |
| 13 | Sticker |

- `text_data` is inline on the `message` row
- `timestamp` is milliseconds Unix; `message_type=7` = system (filtered by default)
- `sender_jid_row_id` is only set for group messages; 1-on-1 uses chat JID + `from_me`
- `quoted_row_id` does NOT exist in all WhatsApp versions — omit it from queries

Contact name resolution order: `wa_contacts.display_name` → `jid.user` (phone number). `wa.db` is optional; `DataLoader` falls back gracefully.

## Linting Notes

Ruff runs `select = ["ALL"]` with a targeted ignore list. Notable active rules: `ANN` (type annotations required everywhere), `S` (security), `PERF`, `UP` (pyupgrade). `disallow_untyped_decorators = false` is set globally because the `@analysis` TypeVar decorator pattern is correct but mypy can't verify it.

## Privacy

All processing is local. Default host is `127.0.0.1`.
