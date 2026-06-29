import logging
import threading
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.bootstrap import init_db_core, migrate_dedup, wait_for_database
from app.config import settings
from app.routers import dashboard, importacao

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(_app: FastAPI):
    misconfigured = settings.is_production and settings.is_sqlite
    if misconfigured:
        logger.error(
            "DATABASE_URL não configurado. Vincule o PostgreSQL e defina "
            "DATABASE_URL=${{Postgres.DATABASE_URL}}. Usando SQLite temporário."
        )

    if not settings.is_sqlite:
        wait_for_database()

    init_db_core()
    threading.Thread(target=migrate_dedup, daemon=True, name="migrate-dedup").start()
    yield


app = FastAPI(
    title="Produtividade Consórcio API",
    description="API de produtividade CIN, CNH e RENAVAM — substitui fonte Excel do Power BI",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins.split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(dashboard.router)
app.include_router(importacao.router)

static_dir = Path(__file__).resolve().parent.parent / "static"
if static_dir.exists():
    app.mount("/static", StaticFiles(directory=static_dir), name="static")


@app.get("/api/health")
def health():
    misconfigured = settings.is_production and settings.is_sqlite
    return {
        "status": "ok" if not misconfigured else "misconfigured",
        "service": "produtividade-api",
        "database": settings.database_kind,
        "persistent": not settings.is_sqlite,
        "message": (
            "Configure DATABASE_URL=${{Postgres.DATABASE_URL}} no Railway."
            if misconfigured
            else None
        ),
    }


@app.get("/favicon.ico", include_in_schema=False)
def favicon():
    path = static_dir / "assets" / "favicon.ico"
    if path.exists():
        return FileResponse(path, media_type="image/x-icon")
    return FileResponse(static_dir / "assets" / "logo-consorcio.png", media_type="image/png")


@app.get("/")
def root():
    index = static_dir / "index.html"
    if index.exists():
        return FileResponse(
            index,
            media_type="text/html; charset=utf-8",
            headers={
                "Cache-Control": "no-store, no-cache, must-revalidate",
                "Pragma": "no-cache",
            },
        )
    return {"message": "API Produtividade Consórcio. Acesse /docs para documentação."}
