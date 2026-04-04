import logging

import dash_bootstrap_components as dbc
from dash import dcc, html

logger = logging.getLogger(__name__)


def layout() -> html.Div:
    return html.Div(
        [
            html.H2("Overview", className="mb-3"),
            dbc.Row(
                [
                    dbc.Col(_stat_card("total-messages", "Messages", "💬"), width=2),
                    dbc.Col(_stat_card("active-days", "Active Days", "📅"), width=2),
                    dbc.Col(_stat_card("total-media", "Media", "🖼️"), width=2),
                    dbc.Col(_stat_card("total-audio", "Voice Notes", "🎙️"), width=2),
                    dbc.Col(_stat_card("total-links", "Links", "🔗"), width=2),
                    dbc.Col(_stat_card("total-reactions", "Reactions", "❤️"), width=2),
                ],
                className="mb-3 g-2",
            ),
            dbc.Row(
                [
                    dbc.Col(
                        dbc.Card(
                            dbc.CardBody(
                                [
                                    html.P("Message Activity (last 30 days)", className="fw-semibold mb-2"),
                                    dcc.Graph(id="overview-sparkline", config={"displayModeBar": False}),
                                ]
                            ),
                        ),
                        width=8,
                    ),
                    dbc.Col(
                        dbc.Card(
                            dbc.CardBody(
                                [
                                    html.P("Message Types", className="fw-semibold mb-2"),
                                    dcc.Graph(id="overview-type-donut", config={"displayModeBar": False}),
                                ]
                            ),
                        ),
                        width=4,
                    ),
                ],
                className="g-2",
            ),
        ]
    )


def _stat_card(stat_id: str, label: str, icon: str) -> dbc.Card:
    return dbc.Card(
        dbc.CardBody(
            [
                html.Div(f"{icon} {label}", style={"fontSize": "0.8rem", "color": "#868e96"}),
                html.Div(id=f"stat-{stat_id}", children="—", style={"fontSize": "1.5rem", "fontWeight": "700"}),
            ]
        ),
    )
