from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import select, text
from sqlalchemy.orm import Session

from app.config import settings
from app.db import Base, engine, get_db
from app import models  # noqa: F401
from app.models import GenerationJob
from app.schemas import GenerationJobCreate, GenerationJobRead


@asynccontextmanager
async def lifespan(_: FastAPI):
    # Local prototype only. Production should use versioned migrations.
    if settings.environment == "development":
        Base.metadata.create_all(bind=engine)
    yield


app = FastAPI(
    title=settings.app_name,
    version="0.1.0",
    description="Self-hostable API foundation. No music model is connected yet.",
    lifespan=lifespan,
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=False,
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type"],
)


def require_development_mode() -> None:
    # There is no user authentication yet. Fail closed outside local development.
    if settings.environment != "development":
        raise HTTPException(
            status_code=503,
            detail="Generation API is disabled until authentication and abuse controls are configured.",
        )


@app.get("/", tags=["system"])
def root() -> dict[str, str]:
    return {"name": settings.app_name, "status": "ok", "docs": "/docs"}


@app.get("/health", tags=["system"])
def health(db: Session = Depends(get_db)) -> dict[str, str]:
    db.execute(text("SELECT 1"))
    engine = "configured" if settings.music_model_backend.strip().lower() == "ace_step" else "not_connected"
    return {"status": "ok", "database": "ok", "music_engine": engine}


@app.post(f"{settings.api_prefix}/generation-jobs", response_model=GenerationJobRead, status_code=202, tags=["generation"], dependencies=[Depends(require_development_mode)])
def create_generation_job(payload: GenerationJobCreate, db: Session = Depends(get_db)) -> GenerationJob:
    job = GenerationJob(
        prompt=payload.prompt.strip(),
        style=payload.style.strip() if payload.style and payload.style.strip() else None,
        instrumental=payload.instrumental,
        status="queued",
    )
    db.add(job)
    db.commit()
    db.refresh(job)
    return job


@app.get(f"{settings.api_prefix}/generation-jobs", response_model=list[GenerationJobRead], tags=["generation"], dependencies=[Depends(require_development_mode)])
def list_generation_jobs(
    limit: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
) -> list[GenerationJob]:
    return list(db.scalars(select(GenerationJob).order_by(GenerationJob.created_at.desc()).limit(limit)))


@app.get(f"{settings.api_prefix}/generation-jobs/{{job_id}}", response_model=GenerationJobRead, tags=["generation"], dependencies=[Depends(require_development_mode)])
def get_generation_job(job_id: str, db: Session = Depends(get_db)) -> GenerationJob:
    job = db.get(GenerationJob, job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Generation job not found")
    return job
