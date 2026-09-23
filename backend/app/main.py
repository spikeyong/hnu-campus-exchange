from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pathlib import Path

from app.api.v1 import router
from app.core.config import settings
from app.db import Base, engine
from app.seed import seed_defaults


@asynccontextmanager
async def lifespan(_: FastAPI):
    if settings.app_env == "production" and settings.secret_key == "development-only-change-me":
        raise RuntimeError("Production requires a strong SECRET_KEY")
    Base.metadata.create_all(bind=engine)
    seed_defaults()
    yield


app = FastAPI(
    title="Hainan University Campus Exchange API",
    version="0.1.0",
    description="Resources, skills, agreements, trust and mutual confirmation.",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.frontend_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router, prefix="/api/v1")
Path(settings.public_upload_dir).mkdir(parents=True, exist_ok=True)
Path(settings.private_upload_dir).mkdir(parents=True, exist_ok=True)
app.mount("/uploads", StaticFiles(directory=settings.public_upload_dir, check_dir=False), name="uploads")


@app.get("/health")
def health_check():
    return {"status": "ok", "environment": settings.app_env}
