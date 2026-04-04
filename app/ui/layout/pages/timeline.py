import logging

import dash_mantine_components as dmc
from dash import dcc, html

logger = logging.getLogger(__name__)


def layout() -> html.Div:
    return html.Div(
        [
            dmc.Title("Timeline", order=2, mb="md"),
            dmc.Card(
                [
                    dmc.Group(
                        [
                            dmc.Text("Granularity", fw=500),
                            dmc.SegmentedControl(
                                id="timeline-period",
                                value="daily",
                                data=[
                                    {"label": "Daily", "value": "daily"},
                                    {"label": "Monthly", "value": "monthly"},
                                ],
                            ),
                        ],
                        mb="md",
                    ),
                    dcc.Graph(id="timeline-chart", config={"displayModeBar": False}),
                ],
                withBorder=True,
                shadow="sm",
                mb="md",
            ),
            dmc.Card(
                [
                    dmc.Text("Activity Heatmap (Day x Hour)", fw=500, mb="sm"),
                    dcc.Graph(id="timeline-heatmap", config={"displayModeBar": False}),
                ],
                withBorder=True,
                shadow="sm",
            ),
        ]
    )
