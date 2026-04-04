import logging

import dash_bootstrap_components as dbc

logger = logging.getLogger(__name__)

_PAGE_TABS = [
    {"value": "/", "label": "Overview"},
    {"value": "/timeline", "label": "Timeline"},
    {"value": "/participants", "label": "Participants"},
    {"value": "/content", "label": "Words & Emoji"},
    {"value": "/media", "label": "Media"},
]


def build_page_tabs(active_path: str) -> dbc.Nav:
    return dbc.Nav(
        [
            dbc.NavItem(
                dbc.NavLink(
                    tab["label"],
                    href=tab["value"],
                    active=(active_path == tab["value"]),
                )
            )
            for tab in _PAGE_TABS
        ],
        pills=True,
        className="mb-3",
    )
