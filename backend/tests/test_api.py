from collections.abc import Generator

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.config import settings
from app.db import Base, get_db
from app import models  # noqa: F401
from app.models import GenerationJob, Track
from app.main import app

test_engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
TestingSessionLocal = sessionmaker(bind=test_engine, autoflush=False, autocommit=False)
Base.metadata.create_all(bind=test_engine)


def override_get_db() -> Generator[Session, None, None]:
    with TestingSessionLocal() as session:
        yield session


app.dependency_overrides[get_db] = override_get_db
client = TestClient(app)


def test_health_reports_engine_not_connected():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"
    assert response.json()["music_engine"] == "not_connected"


def test_health_does_not_claim_configured_engine_is_reachable(monkeypatch):
    monkeypatch.setattr(settings, "music_model_backend", "ace_step")
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["music_engine"] == "configured_unverified"


def test_create_generation_job_queues_without_claiming_generation():
    response = client.post("/api/v1/generation-jobs", json={"prompt": "Warm Nigerian Afrobeats groove", "style": "Afrobeats", "instrumental": True})
    assert response.status_code == 202
    data = response.json()
    assert data["status"] == "queued"
    assert data["style"] == "Afrobeats"
    assert data["instrumental"] is True
    assert data["track"] is None


def test_generation_job_rejects_too_short_prompt():
    response = client.post("/api/v1/generation-jobs", json={"prompt": "ok"})
    assert response.status_code == 422


def test_unknown_job_returns_404():
    response = client.get("/api/v1/generation-jobs/not-a-real-id")
    assert response.status_code == 404


def test_generation_api_is_disabled_outside_development(monkeypatch):
    monkeypatch.setattr(settings, "environment", "production")
    response = client.post("/api/v1/generation-jobs", json={"prompt": "Afrobeat song idea"})
    assert response.status_code == 503
    assert "authentication" in response.json()["detail"]


def test_system_status_does_not_claim_model_is_connected():
    response = client.get("/api/v1/system/status")
    assert response.status_code == 200
    data = response.json()
    assert data["music_engine"] == "not_connected"
    assert data["generation_api_enabled"] is True
    assert data["production_auth_ready"] is False
    assert "not connected" in data["music_engine_message"]


def test_system_status_marks_ace_step_as_unverified(monkeypatch):
    monkeypatch.setattr(settings, "music_model_backend", "ace_step")
    response = client.get("/api/v1/system/status")
    assert response.status_code == 200
    data = response.json()
    assert data["music_engine"] == "configured_unverified"
    assert "not been verified" in data["music_engine_message"]


def test_system_status_shows_generation_disabled_in_production(monkeypatch):
    monkeypatch.setattr(settings, "environment", "production")
    response = client.get("/api/v1/system/status")
    assert response.status_code == 200
    data = response.json()
    assert data["generation_api_enabled"] is False
    assert data["production_auth_ready"] is False


def test_track_library_endpoints_exist():
    response = client.get("/api/v1/tracks")
    assert response.status_code == 200
    assert isinstance(response.json(), list)


def test_unknown_track_returns_404():
    response = client.get("/api/v1/tracks/not-a-real-id")
    assert response.status_code == 404


def test_track_library_is_disabled_outside_development(monkeypatch):
    monkeypatch.setattr(settings, "environment", "production")
    response = client.get("/api/v1/tracks")
    assert response.status_code == 503


def test_completed_generation_job_includes_saved_track_metadata():
    with TestingSessionLocal() as session:
        job = GenerationJob(prompt="Warm Afrobeats groove", status="succeeded")
        session.add(job)
        session.flush()
        track = Track(
            job_id=job.id,
            title="Warm Afrobeats groove",
            audio_key="tracks/test.wav",
            duration_seconds=30,
        )
        session.add(track)
        session.commit()
        job_id = job.id

    response = client.get(f"/api/v1/generation-jobs/{job_id}")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "succeeded"
    assert data["track"]["title"] == "Warm Afrobeats groove"
    assert data["track"]["audio_key"] == "tracks/test.wav"
    assert data["track"]["duration_seconds"] == 30


def test_queued_generation_job_has_no_track():
    response = client.post("/api/v1/generation-jobs", json={"prompt": "Slow soulful R&B"})
    assert response.status_code == 202
    data = response.json()
    assert data["status"] == "queued"
    assert data["track"] is None


def test_generation_job_list_includes_track_when_available():
    with TestingSessionLocal() as session:
        job = GenerationJob(prompt="Instrumental test", status="succeeded")
        session.add(job)
        session.flush()
        session.add(Track(job_id=job.id, title="Instrumental test", audio_key="tracks/test-2.wav", duration_seconds=24))
        session.commit()

    response = client.get("/api/v1/generation-jobs?limit=100")
    assert response.status_code == 200
    matched = [item for item in response.json() if item["prompt"] == "Instrumental test"]
    assert matched
    assert matched[0]["track"]["title"] == "Instrumental test"
