import json
import logging

from dash import ALL, MATCH, Dash, Input, Output, State, callback_context

logger = logging.getLogger(__name__)


def register(app: Dash) -> None:
    @app.callback(
        Output("store-config", "data"),
        Input({"type": "chat-nav-item", "index": ALL}, "n_clicks"),
        State("store-config", "data"),
        prevent_initial_call=True,
    )
    def update_selected_chat(n_clicks: list, current_config: dict) -> dict:
        ctx = callback_context
        if not ctx.triggered or not any(n_clicks):
            return current_config or {}

        triggered_id = ctx.triggered[0]["prop_id"]
        try:
            raw = triggered_id.split(".n_clicks")[0]
            chat_id = json.loads(raw)["index"]
        except KeyError, ValueError:
            logger.warning(f"Failed to parse triggered chat ID: {triggered_id}")
            return current_config or {}

        logger.info(f"Chat selected: {chat_id}")
        config = dict(current_config or {})
        config["chat_id"] = chat_id
        return config

    @app.callback(
        Output({"type": "chat-nav-item", "index": MATCH}, "active"),
        Input("store-config", "data"),
        State({"type": "chat-nav-item", "index": MATCH}, "id"),
    )
    def highlight_active_chat(config_data: dict, nav_id: dict) -> bool:
        if not config_data:
            return False
        return config_data.get("chat_id") == nav_id.get("index")
