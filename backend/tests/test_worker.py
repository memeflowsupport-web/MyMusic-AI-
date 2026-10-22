import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.db import Base
from app.model_runner import GeneratedAudio, ModelNotConfiguredError
from app.models import GenerationJob, Track
from app.storage import LocalAudioStorage
from app.worker import process_one


@pytest.fixture
def session_factory():
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(engine)
    factory = sessionmaker(bind=engine, expire_on_commit=False)
    yield factory
    engine.dispose()


class SuccessfulRunner:
    def generate(self, request):
        assert request.prompt == "Afrobeat at 100 BPM"
        return GeneratedAudio(b"test-audio-bytes", "Test track", 12, ".wav")


class MissingRunner:
    def generate(self, request):
        raise ModelNotConfiguredError("No model installed")


def create_job(factory):
    with factory() as session:
        job = GenerationJob(prompt="Afrobeat at 100 BPM", style="Afrobeat", instrumental=True)
        session.add(job)
        session.commit()
        return job.id


def test_worker_marks_job_failed_when_model_missing(session_factory, tmp_path):
    job_id = create_job(session_factory)
    assert process_one(session_factory, MissingRunner(), LocalAudioStorage(tmp_path))
    with session_factory() as session:
        job = session.get(GenerationJob, job_id)
        assert job.status == "failed"
        assert "No model installed" in job.error_message
        assert session.query(Track).count() == 0


def test_worker_saves_runner_output(session_factory, tmp_path):
    job_id = create_job(session_factory)
    storage = LocalAudioStorage(tmp_path)
    assert process_one(session_factory, SuccessfulRunner(), storage)
    with session_factory() as session:
        job = session.get(GenerationJob, job_id)
        track = session.query(Track).filter_by(job_id=job_id).one()
        assert job.status == "succeeded"
        assert track.title == "Test track"
        assert storage.read(track.audio_key) == b"test-audio-bytes"


def test_worker_returns_false_when_queue_empty(session_factory, tmp_path):
    assert not process_one(session_factory, SuccessfulRunner(), LocalAudioStorage(tmp_path))


def test_storage_rejects_path_traversal(tmp_path):
    storage = LocalAudioStorage(tmp_path)
    with pytest.raises(ValueError):
        storage.read("../secret.txt")
    with pytest.raises(ValueError):
        storage.save(b"audio", "../txt")
