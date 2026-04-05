import logging
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

logger = logging.getLogger(__name__)

_DIST = Path(__file__).parent.parent.parent / "frontend" / "dist"


def create_api(msgstore_path: Path, wadb_path: Path | None = None) -> FastAPI:
    @asynccontextmanager
    async def _lifespan(app: FastAPI) -> AsyncGenerator[None]:
        app.state.msgstore_path = msgstore_path
        app.state.wadb_path = wadb_path
        logger.info(f"API initialized: msgstore={msgstore_path}")
        yield

    app = FastAPI(title="WhatsApp Analyzer API", lifespan=_lifespan)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:5173"],
        allow_methods=["GET"],
        allow_headers=["*"],
    )

    from api.routes import analysis, chats, stats  # noqa: PLC0415

    app.include_router(chats.router, prefix="/api")
    app.include_router(stats.router, prefix="/api")
    app.include_router(analysis.router, prefix="/api")

    if _DIST.exists():
        logger.info(f"Serving frontend from {_DIST}")
        app.mount("/assets", StaticFiles(directory=str(_DIST / "assets")), name="assets")

        @app.get("/{full_path:path}", include_in_schema=False)
        async def serve_spa(full_path: str) -> FileResponse:
            candidate = _DIST / full_path
            if candidate.is_file():
                return FileResponse(str(candidate))
            return FileResponse(str(_DIST / "index.html"))
    else:
        logger.warning(f"Frontend dist not found at {_DIST} — run: cd frontend && npm run build")

    return app
