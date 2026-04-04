import logging

import dash_mantine_components as dmc
from dash import dcc, html

logger = logging.getLogger(__name__)


def layout() -> html.Div:
    return html.Div(
        [
            dmc.Title("Media", order=2, mb="md"),
            dmc.Grid(
                [
                    dmc.GridCol(
                        dmc.Card(
                            [
                                dmc.Text("Media Breakdown", fw=500, mb="sm"),
                                dcc.Graph(id="media-donut", config={"displayModeBar": False}),
                            ],
                            withBorder=True,
                            shadow="sm",
                        ),
                        span=5,
                    ),
                    dmc.GridCol(
                        dmc.Card(
                            [
                                dmc.Text("Media Over Time", fw=500, mb="sm"),
                                dcc.Graph(id="media-timeline", config={"displayModeBar": False}),
                            ],
                            withBorder=True,
                            shadow="sm",
                        ),
                        span=7,
                    ),
                ],
                gutter="md",
            ),
        ]
    )
