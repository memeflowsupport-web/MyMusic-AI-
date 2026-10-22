from collections.abc import Generator

import pytest

from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from app.config import settings
from app.db import Base, get_db
from app import models  # noqa: F401
from app.models import GenerationJob, Track, User
from app.storage import LocalAudioStorage
from app.main import app

test_engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
TestingSessionLocal = sessionmaker(bind=test_engine, autoflush=False, autocommit=False)
Base.metadata.create_all(bind=test_engine)


def override_get_db() -> Generator[Session, None, None]:
    with TestingSessionLocal() as session:
        yield session


app.dependency_overrides[get_db] = override_get_db
client = TestClient(app)


@pytest.fixture(autouse=True)
def reset_auth_rate_limits():
    from app import auth as auth_module

    with auth_module._attempts_lock:
        auth_module._attempts.clear()
    yield
    with auth_module._attempts_lock:
        auth_module._attempts.clear()


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



def test_saved_track_audio_endpoint_streams_completed_audio(monkeypatch, tmp_path):
    monkeypatch.setattr(settings, "audio_storage_dir", str(tmp_path))
    audio_key = LocalAudioStorage(tmp_path).save(b"fake-wav-audio", ".wav")
    with TestingSessionLocal() as session:
        job = GenerationJob(prompt="Playback test", status="succeeded")
        session.add(job)
        session.flush()
        track = Track(job_id=job.id, title="Playback test", audio_key=audio_key, duration_seconds=5)
        session.add(track)
        session.commit()
        track_id = track.id

    response = client.get(f"/api/v1/tracks/{track_id}/audio")
    assert response.status_code == 200
    assert response.content == b"fake-wav-audio"
    assert response.headers["content-type"].startswith("audio/wav")
    assert response.headers["cache-control"] == "private, no-store"
    assert response.headers["x-content-type-options"] == "nosniff"


def test_audio_endpoint_hides_missing_audio_file(monkeypatch, tmp_path):
    monkeypatch.setattr(settings, "audio_storage_dir", str(tmp_path))
    with TestingSessionLocal() as session:
        job = GenerationJob(prompt="Missing audio test", status="succeeded")
        session.add(job)
        session.flush()
        track = Track(job_id=job.id, title="Missing audio test", audio_key="missing.wav", duration_seconds=5)
        session.add(track)
        session.commit()
        track_id = track.id

    response = client.get(f"/api/v1/tracks/{track_id}/audio")
    assert response.status_code == 404
    assert response.json()["detail"] == "Audio file not found"


def test_audio_endpoint_rejects_track_not_completed():
    with TestingSessionLocal() as session:
        job = GenerationJob(prompt="Not ready test", status="running")
        session.add(job)
        session.flush()
        track = Track(job_id=job.id, title="Not ready test", audio_key="not-ready.wav", duration_seconds=5)
        session.add(track)
        session.commit()
        track_id = track.id

    response = client.get(f"/api/v1/tracks/{track_id}/audio")
    assert response.status_code == 409


def test_audio_endpoint_is_disabled_outside_development(monkeypatch):
    monkeypatch.setattr(settings, "environment", "production")
    response = client.get("/api/v1/tracks/some-track-id/audio")
    assert response.status_code == 503



def test_interactive_api_docs_are_available_in_development():
    # The test app is initialized with the development environment by default.
    assert client.get("/docs").status_code == 200
    assert client.get("/redoc").status_code == 200
    assert client.get("/openapi.json").status_code == 200



def test_authentication_is_disabled_by_default(monkeypatch):
    monkeypatch.setattr(settings, "auth_enabled", False)
    monkeypatch.setattr(settings, "auth_secret_key", "x" * 40)
    response = client.post(
        "/api/v1/auth/register",
        json={"email": "disabled@example.com", "password": "long-enough-test-password"},
    )
    assert response.status_code == 503


def test_register_login_and_current_user(monkeypatch):
    monkeypatch.setattr(settings, "auth_enabled", True)
    monkeypatch.setattr(settings, "auth_secret_key", "test-only-secret-key-that-is-long-enough-123456")
    email = "auth-flow@example.com"
    with TestingSessionLocal() as session:
        session.query(User).filter(User.email == email).delete()
        session.commit()

    registration = client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": "a-strong-test-password-123"},
    )
    assert registration.status_code == 201
    assert registration.json()["email"] == email
    assert "password" not in registration.json()
    assert "password_hash" not in registration.json()

    duplicate = client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": "a-strong-test-password-123"},
    )
    assert duplicate.status_code == 409

    login_response = client.post(
        "/api/v1/auth/login",
        json={"email": email, "password": "a-strong-test-password-123"},
    )
    assert login_response.status_code == 200
    token_data = login_response.json()
    assert token_data["token_type"] == "bearer"
    assert token_data["expires_in"] == settings.access_token_expire_minutes * 60

    me = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token_data['access_token']}"})
    assert me.status_code == 200
    assert me.json()["id"] == registration.json()["id"]
    assert me.json()["email"] == email


def test_auth_me_rejects_invalid_token(monkeypatch):
    monkeypatch.setattr(settings, "auth_enabled", True)
    monkeypatch.setattr(settings, "auth_secret_key", "test-only-secret-key-that-is-long-enough-123456")
    response = client.get("/api/v1/auth/me", headers={"Authorization": "Bearer not-a-valid-token"})
    assert response.status_code == 401


def test_authenticated_job_is_hidden_from_other_user(monkeypatch):
    from uuid import uuid4
    monkeypatch.setattr(settings, "environment", "development")
    monkeypatch.setattr(settings, "auth_enabled", True)
    monkeypatch.setattr(settings, "auth_secret_key", "test-only-secret-key-that-is-long-enough-123456")
    suffix = str(uuid4())
    tokens = []
    for label in ("a", "b"):
        email = f"ownership-{label}-{suffix}@example.com"
        assert client.post("/api/v1/auth/register", json={"email": email, "password": "owner-test-password-123"}).status_code == 201
        response = client.post("/api/v1/auth/login", json={"email": email, "password": "owner-test-password-123"})
        assert response.status_code == 200
        tokens.append(response.json()["access_token"])
    created = client.post("/api/v1/generation-jobs", json={"prompt": "Private song owned by user A"}, headers={"Authorization": f"Bearer {tokens[0]}"})
    assert created.status_code == 202
    job_id = created.json()["id"]
    assert client.get(f"/api/v1/generation-jobs/{job_id}", headers={"Authorization": f"Bearer {tokens[0]}"}).status_code == 200
    assert client.get(f"/api/v1/generation-jobs/{job_id}", headers={"Authorization": f"Bearer {tokens[1]}"}).status_code == 404
    listing = client.get("/api/v1/generation-jobs", headers={"Authorization": f"Bearer {tokens[1]}"})
    assert all(job["id"] != job_id for job in listing.json())


def test_authenticated_track_metadata_and_audio_are_private(monkeypatch, tmp_path):
    from uuid import uuid4

    monkeypatch.setattr(settings, "environment", "development")
    monkeypatch.setattr(settings, "auth_enabled", True)
    monkeypatch.setattr(settings, "auth_secret_key", "test-only-secret-key-that-is-long-enough-123456")
    monkeypatch.setattr(settings, "audio_storage_dir", str(tmp_path))
    suffix = str(uuid4())
    tokens = []
    for label in ("a", "b"):
        email = f"track-owner-{label}-{suffix}@example.com"
        assert client.post("/api/v1/auth/register", json={"email": email, "password": "owner-test-password-123"}).status_code == 201
        login = client.post("/api/v1/auth/login", json={"email": email, "password": "owner-test-password-123"})
        assert login.status_code == 200
        tokens.append(login.json()["access_token"])

    audio_key = LocalAudioStorage(tmp_path).save(b"private-audio-bytes", ".wav")
    with TestingSessionLocal() as session:
        owner_id = session.scalar(select(User.id).where(User.email == f"track-owner-a-{suffix}@example.com"))
        job = GenerationJob(prompt="Private track A", status="succeeded", owner_id=owner_id)
        session.add(job)
        session.flush()
        track = Track(job_id=job.id, title="Private track A", audio_key=audio_key, duration_seconds=5)
        session.add(track)
        session.commit()
        track_id = track.id

    owner_headers = {"Authorization": f"Bearer {tokens[0]}"}
    other_headers = {"Authorization": f"Bearer {tokens[1]}"}
    assert client.get(f"/api/v1/tracks/{track_id}", headers=owner_headers).status_code == 200
    assert client.get(f"/api/v1/tracks/{track_id}/audio", headers=owner_headers).content == b"private-audio-bytes"
    assert client.get(f"/api/v1/tracks/{track_id}", headers=other_headers).status_code == 404
    assert client.get(f"/api/v1/tracks/{track_id}/audio", headers=other_headers).status_code == 404
    other_listing = client.get("/api/v1/tracks", headers=other_headers)
    assert other_listing.status_code == 200
    assert all(track["id"] != track_id for track in other_listing.json())


def test_auth_login_rate_limit_returns_retry_after(monkeypatch):
    from app import auth as auth_module

    monkeypatch.setattr(settings, "auth_enabled", True)
    monkeypatch.setattr(settings, "auth_secret_key", "test-only-secret-key-that-is-long-enough-123456")
    monkeypatch.setattr(settings, "auth_login_limit", 2)
    monkeypatch.setattr(settings, "auth_login_window_seconds", 900)
    auth_module._attempts.clear()
    for _ in range(2):
        response = client.post("/api/v1/auth/login", json={"email": "nobody@example.com", "password": "wrong-password"})
        assert response.status_code == 401
    limited = client.post("/api/v1/auth/login", json={"email": "nobody@example.com", "password": "wrong-password"})
    assert limited.status_code == 429
    assert int(limited.headers["Retry-After"]) > 0
    auth_module._attempts.clear()
