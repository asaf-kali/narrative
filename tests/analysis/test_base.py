import pandas as pd

from narrative.analysis.base import analysis, get_registered, list_for_page
from narrative.analysis.content import word_frequencies
from narrative.models.config import AnalysisConfig


def test_analysis_decorator_registers_metadata() -> None:
    @analysis(name="_test_dummy_analysis", label="Dummy", page="_test_page", description="desc")
    def _dummy(df: pd.DataFrame, _config: AnalysisConfig) -> pd.DataFrame:
        return df

    meta = get_registered("_test_dummy_analysis")
    assert meta is not None
    assert meta.label == "Dummy"
    assert meta.page == "_test_page"
    assert meta.description == "desc"
    assert meta.fn is _dummy


def test_get_registered_missing_returns_none() -> None:
    assert get_registered("does_not_exist") is None


def test_list_for_page_filters_by_page() -> None:
    results = list_for_page("content")
    assert any(m.fn is word_frequencies for m in results)
    assert all(m.page == "content" for m in results)


def test_list_for_page_empty_for_unknown_page() -> None:
    assert list_for_page("_no_such_page") == []
