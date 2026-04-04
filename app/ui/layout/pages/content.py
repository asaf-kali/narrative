import logging

import dash_mantine_components as dmc
from dash import dcc, html

logger = logging.getLogger(__name__)


def layout() -> html.Div:
    return html.Div(
        [
            dmc.Title("Words & Emoji", order=2, mb="md"),
            dmc.Grid(
                [
                    dmc.GridCol(
                        dmc.Card(
                            [dmc.Text("Word Cloud", fw=500, mb="sm"), html.Div(id="word-cloud-img")],
                            withBorder=True,
                            shadow="sm",
                        ),
                        span=6,
                    ),
                    dmc.GridCol(
                        dmc.Card(
                            [
                                dmc.Text("Top 20 Words", fw=500, mb="sm"),
                                dcc.Graph(id="top-words-chart", config={"displayModeBar": False}),
                            ],
                            withBorder=True,
                            shadow="sm",
                        ),
                        span=6,
                    ),
                ],
                gutter="md",
                mb="md",
            ),
            dmc.Card(
                [
                    dmc.Text("Emoji Usage", fw=500, mb="sm"),
                    dcc.Graph(id="emoji-chart", config={"displayModeBar": False}),
                ],
                withBorder=True,
                shadow="sm",
            ),
        ]
    )
