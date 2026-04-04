import logging

from dash import Dash, Input, Output, html
from ui.layout.pages import content, media, overview, participants, timeline

logger = logging.getLogger(__name__)

_ROUTES: dict[str, object] = {
    "/": overview.layout,
    "/timeline": timeline.layout,
    "/participants": participants.layout,
    "/content": content.layout,
    "/media": media.layout,
}

_NO_CHAT_SELECTED = html.Div(
    "← Select a chat from the sidebar to begin.",
    style={"padding": "40px", "color": "#868e96", "fontSize": "16px"},
)


def register(app: Dash) -> None:
    @app.callback(
        Output("page-content", "children"),
        Input("url", "pathname"),
        Input("store-config", "data"),
    )
    def render_page(pathname: str | None, config_data: dict) -> object:
        if not config_data or not config_data.get("chat_id"):
            return _NO_CHAT_SELECTED

        path = pathname or "/"
        layout_fn = _ROUTES.get(path, overview.layout)
        from ui.layout.shell import build_page_tabs  # noqa: PLC0415

        return [build_page_tabs(path), layout_fn()]
