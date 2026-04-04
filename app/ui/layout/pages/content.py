import logging

import dash_bootstrap_components as dbc
from dash import dcc, html

logger = logging.getLogger(__name__)


def layout() -> html.Div:
    return html.Div(
        [
            html.H2("Words & Emoji", className="mb-3"),
            dbc.Row(
                [
                    dbc.Col(
                        dbc.Card(
                            dbc.CardBody(
                                [
                                    html.P("Word Cloud", className="fw-semibold mb-2"),
                                    html.Div(id="word-cloud-img"),
                                ]
                            ),
                        ),
                        width=6,
                    ),
                    dbc.Col(
                        dbc.Card(
                            dbc.CardBody(
                                [
                                    html.P("Top 20 Words", className="fw-semibold mb-2"),
                                    dcc.Graph(id="top-words-chart", config={"displayModeBar": False}),
                                ]
                            ),
                        ),
                        width=6,
                    ),
                ],
                className="mb-3 g-2",
            ),
            dbc.Card(
                dbc.CardBody(
                    [
                        html.P("Emoji Usage", className="fw-semibold mb-2"),
                        dcc.Graph(id="emoji-chart", config={"displayModeBar": False}),
                    ]
                ),
            ),
        ]
    )
