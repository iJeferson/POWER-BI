from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.bootstrap import init_db
from app.config import settings
from app.routers import dashboard, importacao


@asynccontextmanager
async def lifespan(_app: FastAPI):
    settings.ensure_persistent_database()
    init_db()
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
    return {
        "status": "ok",
        "service": "produtividade-api",
        "database": settings.database_kind,
        "persistent": not settings.is_sqlite,
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
        return FileResponse(index, media_type="text/html; charset=utf-8")
    return {"message": "API Produtividade Consórcio. Acesse /docs para documentação."}
