"""Polling worker foundation. No audio is generated until a real model is configured."""
import logging
import time
from datetime import datetime, timezone

from sqlalchemy import select, update
from sqlalchemy.orm import Session, sessionmaker

from app.db import SessionLocal
from app.model_runner import GenerationRequest, MusicModelRunner, UnconfiguredMusicModel
from app.models import GenerationJob, Track
from app.storage import LocalAudioStorage

logger = logging.getLogger(__name__)


def process_one(
    session_factory: sessionmaker[Session] = SessionLocal,
    runner: MusicModelRunner | None = None,
    storage: LocalAudioStorage | None = None,
) -> bool:
    """Claim and process one job. Return False if queue is empty."""
    runner = runner or UnconfiguredMusicModel()
    storage = storage or LocalAudioStorage()
    with session_factory() as session:
        candidate = session.scalar(
            select(GenerationJob.id).where(GenerationJob.status == "queued")
            .order_by(GenerationJob.created_at).limit(1)
        )
        if candidate is None:
            return False
        claimed = session.execute(
            update(GenerationJob)
            .where(GenerationJob.id == candidate, GenerationJob.status == "queued")
            .values(status="running", updated_at=datetime.now(timezone.utc))
        )
        session.commit()
        if claimed.rowcount != 1:
            return True
        job = session.get(GenerationJob, candidate)
        if job is None:
            return True
        request = GenerationRequest(job.prompt, job.style, job.instrumental)
        try:
            audio = runner.generate(request)
            if not audio.data:
                raise ValueError("The model returned empty audio data.")
            if audio.duration_seconds <= 0:
                raise ValueError("The model returned an invalid duration.")
            key = storage.save(audio.data, audio.suffix)
            session.add(Track(job_id=job.id, title=audio.title[:180] or "Generated track",
                              audio_key=key, duration_seconds=audio.duration_seconds))
            job.status = "succeeded"
            job.error_message = None
        except Exception as exc:
            logger.exception("Generation job %s failed", job.id)
            job.status = "failed"
            job.error_message = str(exc)[:500] or "Generation failed."
        job.updated_at = datetime.now(timezone.utc)
        session.commit()
        return True


def run_forever(poll_seconds: float = 2.0) -> None:
    while True:
        try:
            if not process_one():
                time.sleep(max(0.25, poll_seconds))
        except KeyboardInterrupt:
            logger.info("Worker stopped.")
            return
        except Exception:
            logger.exception("Worker loop error")
            time.sleep(max(1.0, poll_seconds))


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    run_forever()
