from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from sqlalchemy import select, text
from sqlalchemy.orm import Session, selectinload

from app.config import settings
from app.db import Base, engine, get_db
from app import models  # noqa: F401
from app.models import GenerationJob, Track
from app.storage import LocalAudioStorage
from app.schemas import GenerationJobCreate, GenerationJobRead, TrackRead


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
    engine = "configured_unverified" if settings.music_model_backend.strip().lower() == "ace_step" else "not_connected"
    return {"status": "ok", "database": "ok", "music_engine": engine}


@app.get(f"{settings.api_prefix}/system/status", tags=["system"])
def system_status() -> dict[str, str | bool]:
    """Report setup readiness without exposing secrets or claiming model reachability."""
    backend = settings.music_model_backend.strip().lower()
    if backend == "ace_step":
        engine_status = "configured_unverified"
        engine_message = "ACE-Step adapter selected; live model server has not been verified."
    else:
        engine_status = "not_connected"
        engine_message = "Music model not connected."

    return {
        "application": settings.app_name,
        "environment": settings.environment,
        "database_configuration": "configured",
        "music_engine": engine_status,
        "music_engine_message": engine_message,
        "generation_api_enabled": settings.environment == "development",
        "production_auth_ready": False,
    }


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
    statement = select(GenerationJob).options(selectinload(GenerationJob.track)).order_by(GenerationJob.created_at.desc()).limit(limit)
    return list(db.scalars(statement))


@app.get(f"{settings.api_prefix}/generation-jobs/{{job_id}}", response_model=GenerationJobRead, tags=["generation"], dependencies=[Depends(require_development_mode)])
def get_generation_job(job_id: str, db: Session = Depends(get_db)) -> GenerationJob:
    statement = select(GenerationJob).options(selectinload(GenerationJob.track)).where(GenerationJob.id == job_id)
    job = db.scalar(statement)
    if job is None:
        raise HTTPException(status_code=404, detail="Generation job not found")
    return job


@app.get(f"{settings.api_prefix}/tracks", response_model=list[TrackRead], tags=["tracks"], dependencies=[Depends(require_development_mode)])
def list_tracks(
    limit: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
) -> list[Track]:
    """List saved track metadata, newest first. Audio files are not exposed publicly."""
    return list(db.scalars(select(Track).order_by(Track.created_at.desc()).limit(limit)))


@app.get(f"{settings.api_prefix}/tracks/{{track_id}}", response_model=TrackRead, tags=["tracks"], dependencies=[Depends(require_development_mode)])
def get_track(track_id: str, db: Session = Depends(get_db)) -> Track:
    track = db.get(Track, track_id)
    if track is None:
        raise HTTPException(status_code=404, detail="Track not found")
    return track


@app.get(f"{settings.api_prefix}/tracks/{{track_id}}/audio", tags=["tracks"], dependencies=[Depends(require_development_mode)])
def play_track_audio(track_id: str, db: Session = Depends(get_db)) -> FileResponse:
    """Stream a completed track inline; this route is disabled outside development until auth exists."""
    track = db.get(Track, track_id)
    if track is None:
        raise HTTPException(status_code=404, detail="Track not found")
    if track.job.status != "succeeded":
        raise HTTPException(status_code=409, detail="Track is not ready for playback")
    if not track.audio_key:
        raise HTTPException(status_code=404, detail="Audio file not found")

    try:
        audio_path = LocalAudioStorage().path_for_read(track.audio_key)
    except (ValueError, FileNotFoundError):
        raise HTTPException(status_code=404, detail="Audio file not found") from None

    media_types = {
        ".wav": "audio/wav",
        ".mp3": "audio/mpeg",
        ".ogg": "audio/ogg",
        ".flac": "audio/flac",
        ".m4a": "audio/mp4",
        ".aac": "audio/aac",
        ".opus": "audio/ogg",
    }
    media_type = media_types.get(audio_path.suffix.lower())
    if media_type is None:
        raise HTTPException(status_code=415, detail="Unsupported audio format")

    return FileResponse(
        audio_path,
        media_type=media_type,
        headers={"Cache-Control": "private, no-store", "X-Content-Type-Options": "nosniff"},
    )
