from narrative.semantic_search import params


def test_defaults_are_positive_integers() -> None:
    assert params.DEFAULT_GAP_SECONDS > 0
    assert params.DEFAULT_BATCH_SIZE > 0
    assert params.DEFAULT_CHUNK_SIZE > 0
    assert params.DEFAULT_MIN_SESSION_CHARS > 0
    assert params.DEFAULT_MAX_SESSION_MESSAGES > 0
    assert params.DEFAULT_RERANK_CANDIDATES > 0


def test_gap_seconds_is_two_hours() -> None:
    assert params.DEFAULT_GAP_SECONDS == 60 * 60 * 2
