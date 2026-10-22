from fastapi.testclient import TestClient

from app.config import settings
from app.main import app

client = TestClient(app)


def test_health_reports_engine_not_connected():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"
    assert response.json()["music_engine"] == "not_connected"


def test_create_generation_job_queues_without_claiming_generation():
    response = client.post(
        "/api/v1/generation-jobs",
        json={"prompt": "Warm Nigerian Afrobeats groove", "style": "Afrobeats", "instrumental": True},
    )
    assert response.status_code == 202
    data = response.json()
    assert data["status"] == "queued"
    assert data["style"] == "Afrobeats"
    assert data["instrumental"] is True


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
