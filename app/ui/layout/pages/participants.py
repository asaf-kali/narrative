import logging

import dash_bootstrap_components as dbc
from dash import dcc, html

logger = logging.getLogger(__name__)


def layout() -> html.Div:
    return html.Div(
        [
            html.H2("Participants", className="mb-3"),
            dbc.Card(
                dbc.CardBody(
                    [
                        html.P("Message Distribution", className="fw-semibold mb-2"),
                        dcc.Graph(id="participants-bar", config={"displayModeBar": False}),
                    ]
                ),
                className="mb-3",
            ),
            dbc.Card(
                dbc.CardBody(
                    [
                        html.P("Detailed Stats", className="fw-semibold mb-2"),
                        html.Div(id="participants-table"),
                    ]
                ),
            ),
        ]
    )
