import logging

import dash_bootstrap_components as dbc
from dash import dcc, html

logger = logging.getLogger(__name__)


def layout() -> html.Div:
    return html.Div(
        [
            html.H2("Media", className="mb-3"),
            dbc.Row(
                [
                    dbc.Col(
                        dbc.Card(
                            dbc.CardBody(
                                [
                                    html.P("Media Breakdown", className="fw-semibold mb-2"),
                                    dcc.Graph(id="media-donut", config={"displayModeBar": False}),
                                ]
                            ),
                        ),
                        width=5,
                    ),
                    dbc.Col(
                        dbc.Card(
                            dbc.CardBody(
                                [
                                    html.P("Media Over Time", className="fw-semibold mb-2"),
                                    dcc.Graph(id="media-timeline", config={"displayModeBar": False}),
                                ]
                            ),
                        ),
                        width=7,
                    ),
                ],
                className="g-2",
            ),
        ]
    )
