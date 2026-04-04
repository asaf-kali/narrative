import logging

import dash_mantine_components as dmc

logger = logging.getLogger(__name__)

_PAGE_TABS = [
    {"value": "/", "label": "Overview"},
    {"value": "/timeline", "label": "Timeline"},
    {"value": "/participants", "label": "Participants"},
    {"value": "/content", "label": "Words & Emoji"},
    {"value": "/media", "label": "Media"},
]


def build_page_tabs(active_path: str) -> dmc.Tabs:
    return dmc.Tabs(
        value=active_path,
        id="page-tabs",
        children=[
            dmc.TabsList(
                [dmc.TabsTab(tab["label"], value=tab["value"]) for tab in _PAGE_TABS],
                mb="md",
            ),
        ],
    )
