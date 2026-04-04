# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

```bash
just lint          # format + ruff fix + pre-commit
just test          # pytest
just test path/to/test_file.py::test_name  # single test
just cover         # tests + HTML coverage report
just run --msgstore etc/msgstore.db --wadb etc/wa.db  # run dashboard
just run-dev ...   # hot-reload (DASH_DEBUG=true)
```

mypy runs via `uv run dmypy run .` (daemon). UI layer (`app/ui/`) is excluded from mypy — Dash lacks complete type stubs.

## Architecture

4 strict layers. `PYTHONPATH=app` so imports are e.g. `from db.loaders import DataLoader`.

**`app/db/`** — Read-only SQLite access. `DBConnection` is a context manager opening `msgstore.db` (required) and `wa.db` (optional). `DataLoader` resolves contact names, normalizes timestamps to local tz, and returns `pd.DataFrame`. Key schema facts:
- `text_data` is inline on the `message` row (not in `message_text`)
- `timestamp` is milliseconds Unix; `message_type=7` = system (filtered by default)
- `sender_jid_row_id` is only set for group messages; 1-on-1 uses chat JID + `from_me`

**`app/models/`** — Pydantic used for config and summaries only (never per-row). `AnalysisConfig.cache_key()` is the LRU cache key.

**`app/analysis/`** — Pure functions `(pd.DataFrame, AnalysisConfig) → pd.DataFrame`. Register with:
```python
@analysis(name="my_metric", label="My Metric", page="overview")
def my_metric(df: pd.DataFrame, config: AnalysisConfig) -> pd.DataFrame: ...
```
No other registration needed. `app/cache.py` is an LRU-20 dict cache used by the UI callbacks.

**`app/ui/`** — Plotly Dash + dash-mantine-components (Mantine v7). `serve_locally=True` (no CDN). Data flows: chat selection → `dcc.Store("store-config")` → callbacks call `_load_df(config)` → analysis functions → Plotly figures. To add a chart: add layout component + one callback in `app/ui/callbacks/charts.py`.

**`app/data/stopwords/`** — `en.txt` and `he.txt` loaded at import time by `analysis/content.py`.

**`etc/`** — Gitignored. Place `msgstore.db` and `wa.db` here.

## Testing

Tests use in-memory SQLite fixtures defined in `test/conftest.py`:
- `in_memory_msgstore` — seeded SQLite connection with 2 chats and 6 messages
- `sample_messages_df` — pre-built DataFrame for analysis layer tests (bypasses DB entirely)

Patch via `mock.patch.object` in fixtures, never inside test functions. Tests import directly from the layer under test (e.g. `from analysis.timeline import daily_timeline`) — no `app.` prefix needed due to `PYTHONPATH=app`.

## WhatsApp DB Schema Notes

The real schema varies by WhatsApp version. Queries in `app/db/queries/` are written defensively — `reactions.py` and `calls.py` catch `sqlite3.OperationalError` if tables are absent. Key `message_type` values:

| Value | Type |
|-------|------|
| 0 | Text |
| 1 | Image |
| 2 | Audio / Voice note |
| 3 | Video |
| 7 | System notification (filtered by default) |
| 9 | Document |
| 13 | Sticker |

Contact name resolution order: `wa_contacts.display_name` → `jid.user` (phone number). `wa.db` is optional; `DataLoader` falls back gracefully.

## Linting Notes

Ruff runs `select = ["ALL"]` with a targeted ignore list. Notable active rules: `ANN` (type annotations required everywhere), `S` (security), `PERF`, `UP` (pyupgrade). The `app/ui/` layer is excluded from mypy but still checked by ruff. `disallow_untyped_decorators = false` is set globally because the `@analysis` TypeVar decorator pattern is correct but mypy can't verify it.

## Privacy

All processing is local. `serve_locally=True` prevents CDN requests. Default host is `127.0.0.1`.
