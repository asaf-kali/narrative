import logging
from pathlib import Path

import dash_mantine_components as dmc
from dash import Dash, dcc, html
from db.connection import DBConnection
from db.loaders import DataLoader
from models.chat import ChatSummary

logger = logging.getLogger(__name__)

_DEFAULT_THEME = {
    "colorScheme": "light",
    "primaryColor": "teal",
    "fontFamily": "Inter, sans-serif",
}


def create_app(msgstore_path: Path, wadb_path: Path | None = None) -> Dash:
    app = Dash(
        __name__,
        serve_locally=True,  # No CDN requests — all assets served locally
        suppress_callback_exceptions=True,
        title="WhatsApp Analyzer",
        update_title=None,
    )

    with DBConnection(msgstore_path=msgstore_path, wadb_path=wadb_path) as db:
        loader = DataLoader(db)
        chats = loader.load_chats()

    app.layout = _build_layout(chats=chats)

    # Register callbacks after layout is set
    from ui.callbacks import charts, filters, routing  # noqa: PLC0415

    filters.register(app)
    routing.register(app)
    charts.register(app)

    return app


def _build_layout(chats: list[ChatSummary]) -> dmc.MantineProvider:
    chat_store_data = [
        {"id": c.chat_id, "name": c.display_name, "type": c.chat_type, "count": c.message_count} for c in chats
    ]

    return dmc.MantineProvider(
        theme=_DEFAULT_THEME,
        children=[
            dcc.Store(id="store-chats", data=chat_store_data),
            dcc.Store(id="store-config", data={}),
            dcc.Location(id="url", refresh=False),
            dmc.AppShell(
                [
                    dmc.AppShellHeader(_build_header(), px="md"),
                    dmc.AppShellNavbar(_build_navbar(chats), p="md"),
                    dmc.AppShellMain(
                        html.Div(id="page-content", style={"padding": "20px"}),
                    ),
                ],
                header={"height": 60},
                navbar={"width": 280, "breakpoint": "sm", "collapsed": {"mobile": True}},
                padding="0",
            ),
        ],
    )


def _build_header() -> list:
    return [
        dmc.Group(
            [
                dmc.Title("WhatsApp Analyzer", order=3, c="teal"),
                dmc.Group(
                    [
                        dmc.Text("All processing is local — no data leaves your device.", size="xs", c="dimmed"),
                    ]
                ),
            ],
            justify="space-between",
            h="100%",
        )
    ]


def _build_navbar(chats: list[ChatSummary]) -> list:
    return [
        dmc.Text("Chats", size="xs", fw=700, c="dimmed", mb="xs"),
        dmc.TextInput(
            id="chat-search",
            placeholder="Search chats...",
            size="sm",
            mb="sm",
        ),
        html.Div(id="chat-list", children=_render_chat_list(chats)),
    ]


def _render_chat_list(chats: list[ChatSummary]) -> list:
    type_icons = {"group": "👥", "direct": "👤", "broadcast": "📢"}
    items = []
    for chat in chats[:100]:  # Cap at 100 items in sidebar
        icon = type_icons.get(chat.chat_type, "💬")
        items.append(
            dmc.NavLink(
                label=f"{icon} {chat.display_name}",
                description=f"{chat.message_count:,} messages",
                id={"type": "chat-nav-item", "index": chat.chat_id},
                active=False,
                variant="subtle",
            )
        )
    return items
