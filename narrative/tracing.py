"""Lightweight per-request tracing.

`TracingMiddleware` times every `/api` request, logs one line per request (WARNING when
slow) and exposes the timings in a `Server-Timing` header, which browser DevTools show in
the Network tab. Code inside a request marks interesting steps with `span()`; spans
outside a request (e.g. startup) are logged at DEBUG instead.
"""

import logging
from collections.abc import Awaitable, Callable, Iterator, MutableMapping
from contextlib import contextmanager
from contextvars import ContextVar
from time import perf_counter
from typing import Any

from pydantic import BaseModel, Field
from starlette.datastructures import MutableHeaders

logger = logging.getLogger(__name__)

type Scope = MutableMapping[str, Any]
type Message = MutableMapping[str, Any]
type Receive = Callable[[], Awaitable[Message]]
type Send = Callable[[Message], Awaitable[None]]
type ASGIApp = Callable[[Scope, Receive, Send], Awaitable[None]]


class Span(BaseModel):
    name: str
    duration_ms: float


class _ResponseStatus(BaseModel):
    """Mutable holder so the `send` wrapper can report the status code back to the middleware."""

    code: int = 0


class RequestTrace(BaseModel):
    spans: list[Span] = Field(default_factory=list)

    def add(self, span: Span) -> None:
        self.spans.append(span)

    def server_timing(self, total_ms: float) -> str:
        entries = [f"{s.name};dur={s.duration_ms:.1f}" for s in self.spans]
        entries.append(f"total;dur={total_ms:.1f}")
        return ", ".join(entries)

    def summary(self) -> str:
        return " ".join(f"{s.name}={s.duration_ms:.1f}ms" for s in self.spans)


_API_PREFIX = "/api"
DEFAULT_SLOW_MS = 1000.0

_current_trace: ContextVar[RequestTrace | None] = ContextVar("current_trace", default=None)


class TracingMiddleware:
    """Pure ASGI middleware (no BaseHTTPMiddleware) so it adds no buffering to responses."""

    def __init__(self, app: ASGIApp, slow_ms: float = DEFAULT_SLOW_MS) -> None:
        self._app = app
        self._slow_ms = slow_ms

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http" or not scope["path"].startswith(_API_PREFIX):
            await self._app(scope, receive, send)
            return

        trace = RequestTrace()
        token = _current_trace.set(trace)
        start = perf_counter()
        status = _ResponseStatus()

        async def send_with_timing(message: Message) -> None:
            if message["type"] == "http.response.start":
                status.code = message["status"]
                headers = MutableHeaders(scope=message)
                total_ms = _elapsed_ms(start=start)
                headers.append("Server-Timing", trace.server_timing(total_ms=total_ms))
            await send(message)

        try:
            await self._app(scope, receive, send_with_timing)
        finally:
            _current_trace.reset(token)
            total_ms = _elapsed_ms(start=start)
            self._log_request(scope=scope, status=status.code, total_ms=total_ms, trace=trace)

    def _log_request(self, scope: Scope, status: int, total_ms: float, trace: RequestTrace) -> None:
        level = logging.WARNING if total_ms >= self._slow_ms else logging.INFO
        target = _request_target(scope=scope)
        summary = trace.summary()
        logger.log(level, f"{scope['method']} {target} {status} {total_ms:.1f}ms {summary}".rstrip())


@contextmanager
def span(name: str) -> Iterator[None]:
    """Time the enclosed block and attach it to the current request's trace."""
    start = perf_counter()
    try:
        yield
    finally:
        duration_ms = _elapsed_ms(start=start)
        _record(name=name, duration_ms=duration_ms)


def _record(name: str, duration_ms: float) -> None:
    trace = _current_trace.get()
    if trace is None:
        logger.debug(f"{name} took {duration_ms:.1f}ms")
        return
    span_entry = Span(name=name, duration_ms=duration_ms)
    trace.add(span=span_entry)


def _elapsed_ms(start: float) -> float:
    return (perf_counter() - start) * 1000


def _request_target(scope: Scope) -> str:
    path: str = scope["path"]
    query: bytes = scope.get("query_string", b"")
    if not query:
        return path
    return f"{path}?{query.decode('latin-1')}"
