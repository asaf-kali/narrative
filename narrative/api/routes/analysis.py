import logging
import subprocess
from base64 import b64encode
from datetime import datetime
from io import BytesIO
from pathlib import Path
from typing import Any, Literal, cast

import pandas as pd
from fastapi import APIRouter, Request

from narrative.analysis.content import build_word_cloud_text, emoji_counts, word_frequencies
from narrative.analysis.media import media_breakdown, media_over_time
from narrative.analysis.network import NetworkGraph, build_coactivity_graph, build_global_graph, build_reaction_graph
from narrative.analysis.participants import per_sender_stats
from narrative.analysis.reactions import emoji_reaction_breakdown, reaction_leaderboard, top_reacted_messages
from narrative.analysis.replies import reply_leaderboard
from narrative.analysis.timeline import active_days_count, daily_timeline, hourly_heatmap, monthly_timeline
from narrative.api.deps import get_df
from narrative.api.routes.messages import _df_to_message_list, _load_contact_cards, _load_engagement_lookups
from narrative.db.loaders import DataLoader, build_messages_df, datetime_to_ms, open_connection
from narrative.db.queries.messages import fetch_messages_metadata, fetch_messages_page
from narrative.models.config import AnalysisConfig
from narrative.models.message import AUDIO_TYPES, MEDIA_TYPES, MessageType
from narrative.models.sender import SenderRegistry

logger = logging.getLogger(__name__)
router = APIRouter()


def _config(
    chat_id: int,
    exclude_system: bool,
    date_from: datetime | None,
    date_to: datetime | None,
) -> AnalysisConfig:
    return AnalysisConfig(
        chat_id=chat_id,
        exclude_system=exclude_system,
        date_from=date_from,
        date_to=date_to,
    )


@router.get("/chats/{chat_id}/overview")
def get_overview(
    chat_id: int,
    request: Request,
    exclude_system: bool = True,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
) -> dict[str, Any]:
    config = _config(chat_id, exclude_system, date_from, date_to)
    df = get_df(request, config)
    if df.empty:
        return {
            "total_messages": 0,
            "active_days": 0,
            "total_media": 0,
            "total_audio": 0,
            "total_links": 0,
            "sparkline": [],
            "type_breakdown": [],
        }

    total_media = int(df["message_type"].isin({t.value for t in MEDIA_TYPES}).sum())
    total_audio = int(df["message_type"].isin({t.value for t in AUDIO_TYPES}).sum())
    total_links = int(df["text_data"].dropna().str.contains("http", na=False).sum())

    # Sparkline: daily totals for the full date range
    sparkline_df = df.groupby("date").size().reset_index(name="count")
    sparkline = [{"date": str(r["date"]), "count": int(r["count"])} for _, r in sparkline_df.iterrows()]

    # Type breakdown
    type_labels = {t.value: t.name.capitalize() for t in MessageType}
    type_counts = df["message_type"].value_counts().reset_index()
    type_counts.columns = pd.Index(["type", "count"])
    type_breakdown = [
        {"label": type_labels.get(int(r["type"]), "Other"), "count": int(r["count"])} for _, r in type_counts.iterrows()
    ]

    return {
        "total_messages": len(df),
        "active_days": active_days_count(df),
        "total_media": total_media,
        "total_audio": total_audio,
        "total_links": total_links,
        "sparkline": sparkline,
        "type_breakdown": type_breakdown,
    }


@router.get("/chats/{chat_id}/timeline")
def get_timeline(
    chat_id: int,
    request: Request,
    period: str = "daily",
    exclude_system: bool = True,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
) -> list[dict[str, Any]]:
    config = _config(chat_id, exclude_system, date_from, date_to)
    df = get_df(request, config)
    if df.empty:
        return []
    if period == "monthly":
        result = monthly_timeline(df, config)
        return [
            {"x": str(r["month"]), "sender_name": str(r["sender_name"]), "count": int(r["count"])}
            for _, r in result.iterrows()
        ]
    result = daily_timeline(df, config)
    return [
        {
            "x": str(r["date"].date() if hasattr(r["date"], "date") else r["date"]),
            "sender_name": str(r["sender_name"]),
            "count": int(r["count"]),
        }
        for _, r in result.iterrows()
    ]


@router.get("/chats/{chat_id}/heatmap")
def get_heatmap(
    chat_id: int,
    request: Request,
    exclude_system: bool = True,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
) -> list[dict[str, Any]]:
    config = _config(chat_id, exclude_system, date_from, date_to)
    df = get_df(request, config)
    if df.empty:
        return []
    heatmap_df = hourly_heatmap(df, config)
    return [
        {"day": str(day), "hour": int(hour), "count": int(heatmap_df.loc[day, hour])}
        for day in heatmap_df.index
        for hour in heatmap_df.columns
    ]


@router.get("/chats/{chat_id}/participants")
def get_participants(
    chat_id: int,
    request: Request,
    exclude_system: bool = True,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
) -> list[dict[str, Any]]:
    config = _config(chat_id, exclude_system, date_from, date_to)
    df = get_df(request, config)
    if df.empty:
        return []
    stats = per_sender_stats(df, config)
    records = stats.fillna(0).to_dict("records")
    for rec in records:
        name = str(rec.get("sender_name", ""))
        phone = str(rec.get("sender_phone", "") or "")
        rec["sender_id"] = "me" if name == "Me" else (phone or name)
    return cast("list[dict[str, Any]]", records)


@router.get("/chats/{chat_id}/words")
def get_words(
    chat_id: int,
    request: Request,
    exclude_system: bool = True,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
) -> dict[str, Any]:
    config = _config(chat_id, exclude_system, date_from, date_to)
    df = get_df(request, config)
    if df.empty:
        return {"frequencies": [], "wordcloud_png": ""}
    freqs = word_frequencies(df, config)
    wordcloud_png = _generate_wordcloud(df)
    return {
        "frequencies": freqs.to_dict("records"),
        "wordcloud_png": wordcloud_png,
    }


@router.get("/chats/{chat_id}/emoji")
def get_emoji(
    chat_id: int,
    request: Request,
    exclude_system: bool = True,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
) -> list[dict[str, Any]]:
    config = _config(chat_id, exclude_system, date_from, date_to)
    df = get_df(request, config)
    if df.empty:
        return []
    return cast("list[dict[str, Any]]", emoji_counts(df, config).to_dict("records"))


@router.get("/chats/{chat_id}/messages")
def get_messages(
    chat_id: int,
    request: Request,
    exclude_system: bool = True,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
    limit: int = 2000,
    offset: int = 0,
    search: str | None = None,
    sender_id: str | None = None,
    sort: Literal["asc", "desc"] = "asc",
) -> dict[str, Any]:
    date_from_ms = datetime_to_ms(date_from) if date_from else None
    date_to_ms = datetime_to_ms(date_to) if date_to else None
    sender_ids = [sender_id] if sender_id else None

    msgstore: Path = request.app.state.msgstore_path
    wadb: Path | None = request.app.state.wadb_path
    registry: SenderRegistry = request.app.state.sender_registry

    with open_connection(msgstore_path=msgstore, wadb_path=wadb) as db:
        meta = fetch_messages_metadata(
            db.msgstore,
            chat_id=chat_id,
            date_from_ms=date_from_ms,
            date_to_ms=date_to_ms,
            exclude_system=exclude_system,
            sender_ids=sender_ids,
            search=search,
        )
        raw_rows = fetch_messages_page(
            db.msgstore,
            chat_id=chat_id,
            date_from_ms=date_from_ms,
            date_to_ms=date_to_ms,
            exclude_system=exclude_system,
            sender_ids=sender_ids,
            search=search,
            sort_asc=sort == "asc",
            limit=limit,
            offset=offset,
        )
        contact_cards_by_msg = _load_contact_cards(db.msgstore, raw_rows=raw_rows)

    if not raw_rows:
        return {"total": 0, "messages": []}

    reactions_by_msg, replies_by_msg = _load_engagement_lookups(request, chat_id=chat_id)
    df = build_messages_df(raw_rows, registry)
    messages = _df_to_message_list(
        df,
        reactions_by_msg=reactions_by_msg,
        replies_by_msg=replies_by_msg,
        contact_cards_by_msg=contact_cards_by_msg,
    )
    return {"total": meta.total, "messages": messages}


@router.get("/chats/{chat_id}/media")
def get_media(
    chat_id: int,
    request: Request,
    exclude_system: bool = True,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
) -> dict[str, Any]:
    config = _config(chat_id, exclude_system, date_from, date_to)
    df = get_df(request, config)
    if df.empty:
        return {"breakdown": [], "timeline": []}
    return {
        "breakdown": media_breakdown(df, config).to_dict("records"),
        "timeline": media_over_time(df, config).to_dict("records"),
    }


@router.get("/chats/{chat_id}/engagement")
def get_engagement(
    chat_id: int,
    request: Request,
    exclude_system: bool = True,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
) -> dict[str, Any]:
    config = _config(chat_id, exclude_system, date_from, date_to)
    df = get_df(request, config)
    msgstore: Path = request.app.state.msgstore_path
    wadb: Path | None = request.app.state.wadb_path
    registry: SenderRegistry = request.app.state.sender_registry
    with open_connection(msgstore_path=msgstore, wadb_path=wadb) as db:
        loader = DataLoader(db, registry=registry)
        reactions_df = loader.load_reactions(chat_id=chat_id)
        replies_df = loader.load_replies(chat_id=chat_id)
    return {
        "emoji_breakdown": emoji_reaction_breakdown(reactions_df).to_dict("records"),
        "reaction_leaderboard": reaction_leaderboard(df, reactions_df).to_dict("records"),
        "top_reacted": top_reacted_messages(df, reactions_df).to_dict("records"),
        "reply_leaderboard": reply_leaderboard(df, replies_df).to_dict("records"),
    }


@router.get("/network")
def get_global_network(
    request: Request,
    mode: str = "coactivity",
    include_me: bool = True,
    exclude_system: bool = True,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
) -> NetworkGraph:
    config = AnalysisConfig(chat_id=None, exclude_system=exclude_system, date_from=date_from, date_to=date_to)
    df = get_df(request, config)
    if mode == "reactions":
        msgstore: Path = request.app.state.msgstore_path
        wadb: Path | None = request.app.state.wadb_path
        with open_connection(msgstore_path=msgstore, wadb_path=wadb) as db:
            reactions_df = DataLoader(db).load_reactions()
        return build_reaction_graph(df, reactions_df, AnalysisConfig())
    return build_global_graph(df, include_me=include_me)


@router.get("/chats/{chat_id}/network")
def get_network(
    chat_id: int,
    request: Request,
    mode: str = "coactivity",
    exclude_system: bool = True,
    date_from: datetime | None = None,
    date_to: datetime | None = None,
) -> NetworkGraph:
    config = _config(chat_id, exclude_system, date_from, date_to)
    df = get_df(request, config)
    if mode == "reactions":
        msgstore: Path = request.app.state.msgstore_path
        wadb: Path | None = request.app.state.wadb_path
        with open_connection(msgstore_path=msgstore, wadb_path=wadb) as db:
            reactions_df = DataLoader(db).load_reactions()
        return build_reaction_graph(df, reactions_df, config)
    return build_coactivity_graph(df, config)


def _generate_wordcloud(df: pd.DataFrame) -> str:
    try:
        from wordcloud import WordCloud  # noqa: PLC0415

        text = build_word_cloud_text(df)
        if not text.strip():
            return ""
        wc = WordCloud(
            width=800,
            height=400,
            background_color="white",
            colormap="viridis",
            font_path=str(_find_unicode_font()),
        ).generate(text)
        buf = BytesIO()
        wc.to_image().save(buf, format="PNG")
        return "data:image/png;base64," + b64encode(buf.getvalue()).decode()
    except Exception:
        logger.exception("Word cloud generation failed")
        return ""


def _find_unicode_font() -> Path | None:
    """Return a font file that covers Hebrew (and other non-Latin scripts).

    Tries fc-list for a Hebrew-capable font; falls back to DejaVu Sans which
    is bundled on most Linux distros and covers the Hebrew Unicode block.
    """
    try:
        fc_list = "/usr/bin/fc-list"  # absolute path avoids S607
        out = subprocess.check_output([fc_list, ":lang=he", "--format=%{file}\n"], text=True, timeout=3)  # noqa: S603
        for line in out.splitlines():
            p = Path(line.strip())
            if p.is_file():
                logger.debug(f"Word cloud font: {p}")
                return p
    except OSError:
        logger.debug("fc-list not available; falling back to DejaVu Sans")
    fallback = Path("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf")
    if fallback.is_file():
        return fallback
    return None
