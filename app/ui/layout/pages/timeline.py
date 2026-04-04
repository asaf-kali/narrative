import logging

import dash_bootstrap_components as dbc
from dash import dcc, html

logger = logging.getLogger(__name__)


def layout() -> html.Div:
    return html.Div(
        [
            html.H2("Timeline", className="mb-3"),
            dbc.Card(
                dbc.CardBody(
                    [
                        html.Div(
                            [
                                html.Span("Granularity: ", className="fw-semibold me-2"),
                                dbc.RadioItems(
                                    id="timeline-period",
                                    options=[
                                        {"label": "Daily", "value": "daily"},
                                        {"label": "Monthly", "value": "monthly"},
                                    ],
                                    value="daily",
                                    inline=True,
                                ),
                            ],
                            className="mb-3",
                        ),
                        dcc.Graph(id="timeline-chart", config={"displayModeBar": False}),
                    ]
                ),
                className="mb-3",
            ),
            dbc.Card(
                dbc.CardBody(
                    [
                        html.P("Activity Heatmap (Day x Hour)", className="fw-semibold mb-2"),
                        dcc.Graph(id="timeline-heatmap", config={"displayModeBar": False}),
                    ]
                ),
            ),
        ]
    )
