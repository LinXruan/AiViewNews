"""FastAPI entry point: lifespan setup, sessions, API routes and static page."""
from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from starlette.middleware.sessions import SessionMiddleware

from . import config, paths, workers
from .api import admin as admin_api
from .api import auth as auth_api
from .api import documents as documents_api
from .api import reports as reports_api
from .api import setup as setup_api
from .api import tasks as tasks_api
from .db import init_db, reset_interrupted_statuses
from .errors import register_exception_handlers
from .services.auth import seed_initial_users


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    paths.ensure_dirs()
    init_db()
    seed_initial_users()
    reset_interrupted_statuses()
    workers.requeue_interrupted()
    yield
    workers.shutdown()


app = FastAPI(title="新闻事件智能解析系统", lifespan=lifespan)
app.add_middleware(
    SessionMiddleware,
    secret_key=config.session_secret(),
    session_cookie="pdfai_session",
    max_age=config.SESSION_MAX_AGE_SECONDS,
    same_site="lax",
    https_only=False,
)
register_exception_handlers(app)
app.include_router(auth_api.router)
app.include_router(setup_api.router)
app.include_router(documents_api.router)
app.include_router(tasks_api.router)
app.include_router(reports_api.router)
app.include_router(admin_api.router)
app.mount("/static", StaticFiles(directory=str(paths.WEB_DIR)), name="static")


@app.get("/api/health", tags=["system"])
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/", include_in_schema=False)
def index() -> FileResponse:
    return FileResponse(paths.WEB_DIR / "index.html")
