import logging
from collections.abc import Callable
from dataclasses import dataclass
from typing import TypeVar

import pandas as pd
from models.config import AnalysisConfig  # ty: ignore[unresolved-import]

logger = logging.getLogger(__name__)

AnalysisFn = Callable[[pd.DataFrame, AnalysisConfig], pd.DataFrame]
_F = TypeVar("_F", bound=AnalysisFn)


@dataclass(frozen=True)
class AnalysisMetadata:
    name: str
    label: str
    page: str
    description: str
    fn: AnalysisFn


_REGISTRY: dict[str, AnalysisMetadata] = {}


def analysis(
    *,
    name: str,
    label: str,
    page: str,
    description: str = "",
) -> Callable[[_F], _F]:
    def decorator(fn: _F) -> _F:
        _REGISTRY[name] = AnalysisMetadata(name=name, label=label, page=page, description=description, fn=fn)
        return fn

    return decorator


def get_registered(name: str) -> AnalysisMetadata | None:
    return _REGISTRY.get(name)


def list_for_page(page: str) -> list[AnalysisMetadata]:
    return [m for m in _REGISTRY.values() if m.page == page]
