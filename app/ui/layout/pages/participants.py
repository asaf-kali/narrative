import logging

import dash_mantine_components as dmc
from dash import dcc, html

logger = logging.getLogger(__name__)


def layout() -> html.Div:
    return html.Div(
        [
            dmc.Title("Participants", order=2, mb="md"),
            dmc.Card(
                [
                    dmc.Text("Message Distribution", fw=500, mb="sm"),
                    dcc.Graph(id="participants-bar", config={"displayModeBar": False}),
                ],
                withBorder=True,
                shadow="sm",
                mb="md",
            ),
            dmc.Card(
                [
                    dmc.Text("Detailed Stats", fw=500, mb="sm"),
                    html.Div(id="participants-table"),
                ],
                withBorder=True,
                shadow="sm",
            ),
        ]
    )
