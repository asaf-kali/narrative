import logging

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from narrative.tracing import TracingMiddleware, span


@pytest.fixture
def traced_client() -> TestClient:
    app = FastAPI()
    app.add_middleware(TracingMiddleware, slow_ms=10_000)

    @app.get("/api/work")
    def work() -> dict[str, bool]:  # sync route: runs in the threadpool
        with span("db.step"):
            pass
        return {"ok": True}

    @app.get("/other")
    def other() -> dict[str, bool]:
        return {"ok": True}

    return TestClient(app)


@pytest.fixture
def slow_client() -> TestClient:
    app = FastAPI()
    app.add_middleware(TracingMiddleware, slow_ms=0)

    @app.get("/api/slow")
    def slow() -> dict[str, bool]:
        return {"ok": True}

    return TestClient(app)


def test_server_timing_header_includes_spans_and_total(traced_client: TestClient) -> None:
    resp = traced_client.get("/api/work")
    timing = resp.headers["server-timing"]
    assert "db.step;dur=" in timing
    assert "total;dur=" in timing


def test_non_api_paths_are_not_traced(traced_client: TestClient) -> None:
    resp = traced_client.get("/other")
    assert "server-timing" not in resp.headers


def test_request_is_logged_with_spans(traced_client: TestClient, caplog: pytest.LogCaptureFixture) -> None:
    with caplog.at_level(logging.INFO, logger="narrative.tracing"):
        traced_client.get("/api/work", params={"x": "1"})
    record = next(r for r in caplog.records if "/api/work" in r.getMessage())
    assert record.levelno == logging.INFO
    assert "GET /api/work?x=1 200" in record.getMessage()
    assert "db.step=" in record.getMessage()


def test_slow_request_logs_warning(slow_client: TestClient, caplog: pytest.LogCaptureFixture) -> None:
    with caplog.at_level(logging.INFO, logger="narrative.tracing"):
        slow_client.get("/api/slow")
    record = next(r for r in caplog.records if "/api/slow" in r.getMessage())
    assert record.levelno == logging.WARNING


def test_span_outside_request_does_not_raise(caplog: pytest.LogCaptureFixture) -> None:
    with caplog.at_level(logging.DEBUG, logger="narrative.tracing"), span("startup.step"):
        pass
    assert any("startup.step took" in r.getMessage() for r in caplog.records)
