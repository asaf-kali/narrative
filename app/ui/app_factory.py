import logging
from pathlib import Path

import dash_bootstrap_components as dbc
from dash import Dash, dcc, html
from db.connection import DBConnection
from db.loaders import DataLoader
from models.chat import ChatSummary

logger = logging.getLogger(__name__)

_SIDEBAR_STYLE = {
    "position": "fixed",
    "top": "56px",
    "left": 0,
    "bottom": 0,
    "width": "280px",
    "padding": "16px",
    "backgroundColor": "#f8f9fa",
    "borderRight": "1px solid #dee2e6",
    "overflowY": "auto",
}

_CONTENT_STYLE = {
    "marginLeft": "280px",
    "padding": "20px",
    "minHeight": "calc(100vh - 56px)",
}


def create_app(msgstore_path: Path, wadb_path: Path | None = None) -> Dash:
    logger.info("Creating Dash app")
    # assets_folder points to app/assets/ where bootstrap.min.css lives — no CDN requests.
    _assets = str(Path(__file__).parent.parent / "assets")
    app = Dash(
        __name__,
        assets_folder=_assets,
        suppress_callback_exceptions=True,
        title="WhatsApp Analyzer",
        update_title=None,
    )

    with DBConnection(msgstore_path=msgstore_path, wadb_path=wadb_path) as db:
        loader = DataLoader(db)
        chats = loader.load_chats()

    logger.info(f"Loaded {len(chats)} chats for sidebar")
    app.layout = _build_layout(chats=chats)

    # Register callbacks after layout is set
    from ui.callbacks import charts, filters, routing  # noqa: PLC0415

    filters.register(app)
    routing.register(app)
    charts.register(app)
    logger.info("All callbacks registered")

    return app


def _build_layout(chats: list[ChatSummary]) -> html.Div:
    chat_store_data = [
        {"id": c.chat_id, "name": c.display_name, "type": c.chat_type, "count": c.message_count} for c in chats
    ]

    return html.Div(
        [
            dcc.Store(id="store-chats", data=chat_store_data),
            dcc.Store(id="store-config", data={}),
            dcc.Location(id="url", refresh=False),
            _build_navbar(),
            _build_sidebar(chats),
            html.Div(id="page-content", style=_CONTENT_STYLE),
        ]
    )


def _build_navbar() -> dbc.Navbar:
    return dbc.Navbar(
        dbc.Container(
            [
                dbc.NavbarBrand("WhatsApp Analyzer", style={"color": "white", "fontWeight": "600"}),
                html.Span(
                    "All processing is local — no data leaves your device.",
                    style={"color": "rgba(255,255,255,0.7)", "fontSize": "0.8rem"},
                ),
            ],
            fluid=True,
        ),
        color="teal",
        dark=True,
        style={"position": "fixed", "top": 0, "left": 0, "right": 0, "zIndex": 1000},
    )


def _build_sidebar(chats: list[ChatSummary]) -> html.Div:
    return html.Div(
        [
            html.P(
                "CHATS", style={"fontSize": "0.7rem", "fontWeight": "700", "color": "#868e96", "marginBottom": "8px"}
            ),
            dbc.Input(id="chat-search", placeholder="Search chats...", size="sm", className="mb-2"),
            html.Div(id="chat-list", children=_render_chat_list(chats)),
        ],
        style=_SIDEBAR_STYLE,
    )


def _render_chat_list(chats: list[ChatSummary]) -> list:
    type_icons = {"group": "👥", "direct": "👤", "broadcast": "📢"}
    items = []
    for chat in chats[:100]:  # Cap at 100 items in sidebar
        icon = type_icons.get(chat.chat_type, "💬")
        items.append(
            dbc.Button(
                [
                    html.Div(f"{icon} {chat.display_name}", style={"fontWeight": "500", "fontSize": "0.85rem"}),
                    html.Div(f"{chat.message_count:,} messages", style={"fontSize": "0.75rem", "color": "#868e96"}),
                ],
                id={"type": "chat-nav-item", "index": chat.chat_id},
                color="light",
                outline=True,
                style={"width": "100%", "textAlign": "left", "marginBottom": "4px", "padding": "8px 12px"},
                n_clicks=0,
            )
        )
    return items
