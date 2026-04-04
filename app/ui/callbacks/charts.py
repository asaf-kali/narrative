import logging
from base64 import b64encode
from io import BytesIO
from pathlib import Path

import cache
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from analysis.content import build_word_cloud_text, emoji_counts, word_frequencies
from analysis.media import media_breakdown, media_over_time
from analysis.participants import per_sender_stats
from analysis.timeline import active_days_count, daily_timeline, hourly_heatmap, monthly_timeline
from dash import Dash, Input, Output, html
from db.loaders import DataLoader, open_connection
from models.config import AnalysisConfig
from models.message import AUDIO_TYPES, MEDIA_TYPES

logger = logging.getLogger(__name__)

_MSGSTORE_PATH: Path | None = None
_WADB_PATH: Path | None = None


def configure_paths(msgstore: Path, wadb: Path | None = None) -> None:
    global _MSGSTORE_PATH, _WADB_PATH  # noqa: PLW0603
    _MSGSTORE_PATH = msgstore
    _WADB_PATH = wadb


def _load_df(config: AnalysisConfig) -> pd.DataFrame:
    key = config.cache_key()
    cached = cache.get_cached(key)
    if cached is not None:
        logger.debug(f"Cache hit for key={key}")
        return cached

    if _MSGSTORE_PATH is None:
        logger.warning("_load_df called before configure_paths()")
        return pd.DataFrame()

    logger.info(f"Cache miss — loading messages from DB (chat_id={config.chat_id})")
    with open_connection(_MSGSTORE_PATH, _WADB_PATH) as db:
        loader = DataLoader(db)
        df = loader.load_messages(config)

    logger.info(f"Loaded {len(df)} messages for chat_id={config.chat_id}")
    cache.set_cached(key, df)
    return df


def _empty_figure(message: str = "No data") -> go.Figure:
    fig = go.Figure()
    fig.add_annotation(text=message, x=0.5, y=0.5, showarrow=False, font={"size": 14, "color": "#868e96"})
    fig.update_layout(
        xaxis={"visible": False}, yaxis={"visible": False}, paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)"
    )
    return fig


def register(app: Dash) -> None:  # noqa: PLR0915, C901
    # ── Stats cards ──────────────────────────────────────────────────────────

    @app.callback(
        Output("stat-total-messages", "children"),
        Output("stat-active-days", "children"),
        Output("stat-total-media", "children"),
        Output("stat-total-audio", "children"),
        Output("stat-total-links", "children"),
        Output("stat-total-reactions", "children"),
        Input("store-config", "data"),
    )
    def update_stats(config_data: dict) -> tuple:
        if not config_data or not config_data.get("chat_id"):
            return ("—",) * 6
        config = AnalysisConfig(**config_data)
        df = _load_df(config)
        if df.empty:
            return ("—",) * 6

        total = f"{len(df):,}"
        days = f"{active_days_count(df):,}"
        media = f"{df['message_type'].isin({t.value for t in MEDIA_TYPES}).sum():,}"
        audio = f"{df['message_type'].isin({t.value for t in AUDIO_TYPES}).sum():,}"
        links = f"{df['text_data'].dropna().str.contains('http', na=False).sum():,}"
        reactions = "—"  # Loaded separately; placeholder for now

        return total, days, media, audio, links, reactions

    # ── Overview sparkline ───────────────────────────────────────────────────

    @app.callback(
        Output("overview-sparkline", "figure"),
        Output("overview-type-donut", "figure"),
        Input("store-config", "data"),
    )
    def update_overview_charts(config_data: dict) -> tuple[go.Figure, go.Figure]:
        if not config_data or not config_data.get("chat_id"):
            return _empty_figure("Select a chat"), _empty_figure("Select a chat")
        config = AnalysisConfig(**config_data)
        df = _load_df(config)
        if df.empty:
            return _empty_figure("No messages"), _empty_figure("No messages")

        # Sparkline: last 30 days
        last_30 = df[df["timestamp"] >= df["timestamp"].max() - pd.Timedelta(days=30)]
        daily = last_30.groupby("date").size().reset_index(name="count")
        daily["date"] = pd.to_datetime(daily["date"])
        sparkline = px.area(daily, x="date", y="count", labels={"date": "", "count": "Messages"})
        sparkline.update_layout(margin={"t": 10, "b": 10, "l": 10, "r": 10}, height=180)

        # Type donut
        from models.message import MessageType  # noqa: PLC0415

        type_counts = df["message_type"].value_counts().reset_index()
        type_counts.columns = ["type", "count"]
        type_labels = {t.value: t.name.capitalize() for t in MessageType}
        type_counts["label"] = type_counts["type"].map(type_labels).fillna("Other")
        donut = px.pie(type_counts, values="count", names="label", hole=0.5)
        donut.update_layout(margin={"t": 10, "b": 10, "l": 10, "r": 10}, height=180, showlegend=True)

        return sparkline, donut

    # ── Timeline ─────────────────────────────────────────────────────────────

    @app.callback(
        Output("timeline-chart", "figure"),
        Input("store-config", "data"),
        Input("timeline-period", "value"),
    )
    def update_timeline(config_data: dict, period: str) -> go.Figure:
        if not config_data or not config_data.get("chat_id"):
            return _empty_figure("Select a chat")
        config = AnalysisConfig(**config_data)
        df = _load_df(config)
        if df.empty:
            return _empty_figure("No messages")

        if period == "monthly":
            data = monthly_timeline(df, config)
            fig = px.area(
                data,
                x="month",
                y="count",
                color="sender_name",
                labels={"month": "Month", "count": "Messages", "sender_name": "Sender"},
            )
        else:
            data = daily_timeline(df, config)
            fig = px.area(
                data,
                x="date",
                y="count",
                color="sender_name",
                labels={"date": "Date", "count": "Messages", "sender_name": "Sender"},
            )

        fig.update_layout(margin={"t": 20, "b": 20}, height=350)
        return fig

    @app.callback(
        Output("timeline-heatmap", "figure"),
        Input("store-config", "data"),
    )
    def update_heatmap(config_data: dict) -> go.Figure:
        if not config_data or not config_data.get("chat_id"):
            return _empty_figure("Select a chat")
        config = AnalysisConfig(**config_data)
        df = _load_df(config)
        if df.empty:
            return _empty_figure("No messages")

        heatmap_df = hourly_heatmap(df, config)
        fig = go.Figure(
            go.Heatmap(
                z=heatmap_df.values,
                x=[f"{h:02d}:00" for h in heatmap_df.columns],
                y=heatmap_df.index.tolist(),
                colorscale="Teal",
                hovertemplate="%{y} %{x}: %{z} messages<extra></extra>",
            )
        )
        fig.update_layout(margin={"t": 10, "b": 20}, height=280)
        return fig

    # ── Participants ──────────────────────────────────────────────────────────

    @app.callback(
        Output("participants-bar", "figure"),
        Output("participants-table", "children"),
        Input("store-config", "data"),
    )
    def update_participants(config_data: dict) -> tuple:
        if not config_data or not config_data.get("chat_id"):
            return _empty_figure("Select a chat"), "No data"
        config = AnalysisConfig(**config_data)
        df = _load_df(config)
        if df.empty:
            return _empty_figure("No messages"), "No messages"

        stats = per_sender_stats(df, config)
        if stats.empty:
            return _empty_figure("No participant data"), "No data"

        bar = px.bar(
            stats,
            x="messages",
            y="sender_name",
            orientation="h",
            labels={"messages": "Messages", "sender_name": ""},
            color="pct",
            color_continuous_scale="Teal",
        )
        bar.update_layout(margin={"t": 10, "b": 10}, height=max(200, len(stats) * 35), coloraxis_showscale=False)

        from dash import dash_table  # noqa: PLC0415

        table = dash_table.DataTable(
            data=stats.to_dict("records"),
            columns=[
                {"name": "Name", "id": "sender_name"},
                {"name": "Messages", "id": "messages"},
                {"name": "%", "id": "pct"},
                {"name": "Words", "id": "words"},
                {"name": "Avg words/msg", "id": "avg_words"},
                {"name": "Media", "id": "media"},
                {"name": "Audio", "id": "audio"},
            ],
            style_table={"overflowX": "auto"},
            style_cell={"textAlign": "left", "padding": "8px"},
            style_header={"fontWeight": "bold"},
            sort_action="native",
            page_size=20,
        )
        return bar, table

    # ── Word cloud + words ────────────────────────────────────────────────────

    @app.callback(
        Output("word-cloud-img", "children"),
        Output("top-words-chart", "figure"),
        Output("emoji-chart", "figure"),
        Input("store-config", "data"),
    )
    def update_content(config_data: dict) -> tuple:
        empty = (_no_data_placeholder("Select a chat"), _empty_figure("Select a chat"), _empty_figure("Select a chat"))
        if not config_data or not config_data.get("chat_id"):
            return empty
        config = AnalysisConfig(**config_data)
        df = _load_df(config)
        if df.empty:
            return _no_data_placeholder("No messages"), _empty_figure("No messages"), _empty_figure("No messages")

        # Word cloud
        wc_img = _render_word_cloud(df)

        # Top words bar
        words_df = word_frequencies(df, config)
        if words_df.empty:
            words_fig = _empty_figure("No text messages")
        else:
            words_fig = px.bar(
                words_df.head(20),
                x="count",
                y="word",
                orientation="h",
                labels={"count": "Count", "word": ""},
            )
            words_fig.update_layout(margin={"t": 10, "b": 10}, height=400, yaxis={"autorange": "reversed"})

        # Emoji chart
        emoji_df = emoji_counts(df, config)
        if emoji_df.empty:
            emoji_fig = _empty_figure("No emoji found")
        else:
            emoji_fig = px.bar(
                emoji_df.head(20),
                x="count",
                y="emoji",
                orientation="h",
                labels={"count": "Count", "emoji": ""},
            )
            emoji_fig.update_layout(margin={"t": 10, "b": 10}, height=400, yaxis={"autorange": "reversed"})

        return wc_img, words_fig, emoji_fig

    # ── Media ─────────────────────────────────────────────────────────────────

    @app.callback(
        Output("media-donut", "figure"),
        Output("media-timeline", "figure"),
        Input("store-config", "data"),
    )
    def update_media(config_data: dict) -> tuple[go.Figure, go.Figure]:
        if not config_data or not config_data.get("chat_id"):
            return _empty_figure("Select a chat"), _empty_figure("Select a chat")
        config = AnalysisConfig(**config_data)
        df = _load_df(config)
        if df.empty:
            return _empty_figure("No messages"), _empty_figure("No messages")

        breakdown = media_breakdown(df, config)
        donut = (
            px.pie(breakdown, values="count", names="type_label", hole=0.45)
            if not breakdown.empty
            else _empty_figure("No media")
        )
        donut.update_layout(margin={"t": 10, "b": 10}, height=300)

        over_time = media_over_time(df, config)
        timeline_fig = (
            px.bar(
                over_time,
                x="month",
                y="count",
                color="type_label",
                barmode="stack",
                labels={"month": "Month", "count": "Count", "type_label": "Type"},
            )
            if not over_time.empty
            else _empty_figure("No media")
        )
        timeline_fig.update_layout(margin={"t": 10, "b": 10}, height=300)

        return donut, timeline_fig


def _render_word_cloud(df: pd.DataFrame) -> html.Img | html.Div:
    try:
        from wordcloud import WordCloud  # noqa: PLC0415

        text = build_word_cloud_text(df)
        if not text.strip():
            return _no_data_placeholder("No text content")
        wc = WordCloud(width=600, height=300, background_color="white", colormap="viridis").generate(text)
        buf = BytesIO()
        wc.to_image().save(buf, format="PNG")
        encoded = b64encode(buf.getvalue()).decode()
        return html.Img(src=f"data:image/png;base64,{encoded}", style={"width": "100%"})
    except Exception:
        logger.exception("Word cloud generation failed")
        return _no_data_placeholder("Word cloud unavailable")


def _no_data_placeholder(message: str) -> html.Div:
    return html.Div(message, style={"color": "#868e96", "padding": "40px", "textAlign": "center"})
