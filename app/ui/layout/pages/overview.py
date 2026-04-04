import logging

import dash_mantine_components as dmc
from dash import dcc, html

logger = logging.getLogger(__name__)


def layout() -> html.Div:
    return html.Div(
        [
            dmc.Title("Overview", order=2, mb="md"),
            dmc.Grid(
                [
                    dmc.GridCol(
                        dmc.Card(_stat_card("total-messages", "Messages", "💬"), withBorder=True, shadow="sm"), span=2
                    ),
                    dmc.GridCol(
                        dmc.Card(_stat_card("active-days", "Active Days", "📅"), withBorder=True, shadow="sm"), span=2
                    ),
                    dmc.GridCol(
                        dmc.Card(_stat_card("total-media", "Media", "🖼️"), withBorder=True, shadow="sm"), span=2
                    ),
                    dmc.GridCol(
                        dmc.Card(_stat_card("total-audio", "Voice Notes", "🎙️"), withBorder=True, shadow="sm"), span=2
                    ),
                    dmc.GridCol(
                        dmc.Card(_stat_card("total-links", "Links", "🔗"), withBorder=True, shadow="sm"), span=2
                    ),
                    dmc.GridCol(
                        dmc.Card(_stat_card("total-reactions", "Reactions", "❤️"), withBorder=True, shadow="sm"), span=2
                    ),
                ],
                gutter="md",
                mb="xl",
            ),
            dmc.Grid(
                [
                    dmc.GridCol(
                        dmc.Card(
                            [
                                dmc.Text("Message Activity (last 30 days)", fw=500, mb="sm"),
                                dcc.Graph(id="overview-sparkline", config={"displayModeBar": False}),
                            ],
                            withBorder=True,
                            shadow="sm",
                        ),
                        span=8,
                    ),
                    dmc.GridCol(
                        dmc.Card(
                            [
                                dmc.Text("Message Types", fw=500, mb="sm"),
                                dcc.Graph(id="overview-type-donut", config={"displayModeBar": False}),
                            ],
                            withBorder=True,
                            shadow="sm",
                        ),
                        span=4,
                    ),
                ],
                gutter="md",
            ),
        ]
    )


def _stat_card(stat_id: str, label: str, icon: str) -> list:
    return [
        dmc.Group([dmc.Text(icon, size="xl"), dmc.Text(label, size="sm", c="dimmed")]),
        html.Div(id=f"stat-{stat_id}", children=dmc.Text("—", size="xl", fw=700)),
    ]
