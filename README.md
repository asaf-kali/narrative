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
| Poll votes | ❌ | ✅ |
| Reply chains | ❌ | ✅ |
| Deleted messages | ❌ | ✅ |

### Analyses Available

**Overview** — Total messages, active days, media count, reactions, links shared.

**Timeline** — Daily/monthly message volume with per-sender breakdown; activity heatmap by day-of-week and hour.

**Participants** — Per-sender stats table: message count, word count, avg words/message, media sent, voice notes. Percentage share chart.

**Words & Emoji** — Word cloud, top 20 most used words (with Hebrew + English stopword filtering), emoji frequency chart.

**Media** — Media breakdown by type (image, video, voice note, document, sticker, GIF); media volume over time.

---

## Getting the Database Files

Your WhatsApp messages are stored in encrypted SQLite databases on your Android device. To use this tool:

1. Back up your WhatsApp data from your Android device (via WhatsApp Settings → Chats → Chat backup).
2. Locate `msgstore.db.crypt15` (or similar) on your device storage at `Internal Storage/WhatsApp/Databases/`.
3. Decrypt using a tool such as [wa-crypt-tools](https://github.com/ElDavoo/wa-crypt-tools) with your device's backup key.
4. The decrypted `msgstore.db` and optionally `wa.db` (for contact names) are your inputs.

> Your decrypted `.db` files contain all your messages. Keep them secure and never share them.

---

## Prerequisites

- [UV](https://docs.astral.sh/uv/) `>= 0.9`
- [just](https://github.com/casey/just) command runner

---

## Setup

```bash
# 1. Clone and install dependencies
git clone https://github.com/asaf-kali/whatsapp-analyzer
cd whatsapp-analyzer
just install

# 2. Place your decrypted database files in etc/  (gitignored)
mkdir -p etc
cp /path/to/msgstore.db etc/
cp /path/to/wa.db etc/      # optional — needed for contact names

# 3. Run the dashboard
just run --msgstore etc/msgstore.db --wadb etc/wa.db

# Opens at http://127.0.0.1:8050
```

### Options

```
just run --msgstore PATH [--wadb PATH] [--port PORT] [--host HOST]

  --msgstore   Path to decrypted msgstore.db  (required)
  --wadb       Path to decrypted wa.db        (optional, enables contact names)
  --port       Port to listen on              (default: 8050)
  --host       Host to bind to               (default: 127.0.0.1)
```

---

## Development

```bash
just lint          # Format + ruff check + mypy
just test          # Run pytest
just cover         # Run tests with HTML coverage report
just run-dev ...   # Hot-reload mode (set DASH_DEBUG=true)
```

---

## Adding a New Analysis

1. **Write the analysis function** in `app/analysis/` and decorate it:

   ```python
   # app/analysis/my_module.py
   from analysis.base import analysis

   @analysis(name="my_metric", label="My Metric", page="overview")
   def my_metric(df: pd.DataFrame, config: AnalysisConfig) -> pd.DataFrame:
       ...
   ```

2. **Add a chart component** to the corresponding page layout in `app/ui/layout/pages/`:

   ```python
   dcc.Graph(id="my-metric-chart")
   ```

3. **Add a callback** in `app/ui/callbacks/charts.py`:

   ```python
   @app.callback(Output("my-metric-chart", "figure"), Input("store-config", "data"))
   def update_my_metric(config_data: dict) -> go.Figure:
       ...
   ```

That's it — no registration step needed. The `@analysis` decorator handles discovery automatically.

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
                                               Dash callbacks ──▶ Plotly figures
                                                         │
                                                         ▼
                                               Mantine UI (browser, local)
```

**Layers:**

| Layer | Location | Responsibility |
|-------|----------|----------------|
| DB | `app/db/` | Read-only SQLite access, contact name resolution, DataFrame construction |
| Models | `app/models/` | Pydantic types for config, message metadata, chat summaries |
| Analysis | `app/analysis/` | Pure functions: `(pd.DataFrame, AnalysisConfig) → pd.DataFrame` |
| Cache | `app/cache.py` | LRU-20 in-memory cache keyed by `(chat_id, date_range)` |
| UI | `app/ui/` | Dash + dash-mantine-components; callbacks call analysis functions |

---

## Privacy

- **No network calls to external services.** The Dash server runs on `localhost` only (`127.0.0.1` by default). Change to `0.0.0.0` to expose on your LAN — but never expose it to the internet.
- **All assets are served locally.** `serve_locally=True` prevents Dash from loading React/Plotly assets from CDN.
- **`langdetect`** (used for stopword selection) uses bundled language profiles — no network requests.
- **No telemetry, no analytics, no cloud.** This tool reads files from your disk and renders charts in your browser. Nothing leaves your machine.
- The `etc/` directory (where your `.db` files live) is in `.gitignore` and will never be committed.
