import pandas as pd

from narrative.cache import clear_cache, get_cached, set_cached

# Note: the autouse `_clean_module_cache` fixture in conftest.py already isolates
# this singleton between tests; these tests exercise `clear_cache` itself too.


def test_get_cached_missing_key_returns_none() -> None:
    assert get_cached("missing") is None


def test_set_then_get_roundtrip() -> None:
    df = pd.DataFrame({"a": [1, 2]})
    set_cached("key1", df)
    result = get_cached("key1")
    assert result is not None
    pd.testing.assert_frame_equal(result, df)


def test_clear_cache_empties_store() -> None:
    set_cached("key1", pd.DataFrame({"a": [1]}))
    clear_cache()
    assert get_cached("key1") is None


def test_lru_eviction_drops_least_recently_used() -> None:
    for i in range(21):
        set_cached(f"key{i}", pd.DataFrame({"a": [i]}))
    # 21 inserts into a max_size=20 store evicts the first-inserted key.
    assert get_cached("key0") is None
    assert get_cached("key20") is not None


def test_get_marks_key_as_recently_used_protecting_it_from_eviction() -> None:
    for i in range(20):
        set_cached(f"key{i}", pd.DataFrame({"a": [i]}))
    # Touch key0 so it's no longer the least-recently-used entry.
    get_cached("key0")
    set_cached("key20", pd.DataFrame({"a": [20]}))
    assert get_cached("key0") is not None
    assert get_cached("key1") is None


def test_set_existing_key_replaces_value_and_refreshes_recency_without_growing_store() -> None:
    for i in range(20):
        set_cached(f"key{i}", pd.DataFrame({"a": [i]}))
    # Re-setting an existing key replaces the stored value and bumps recency; store stays at 20.
    set_cached("key0", pd.DataFrame({"a": [999]}))
    updated = get_cached("key0")
    assert updated is not None
    assert updated["a"].iloc[0] == 999
    assert get_cached("key1") is not None
