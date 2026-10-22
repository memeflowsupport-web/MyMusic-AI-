import pytest

from app.ace_step_runner import AceStepError, AceStepHttpRunner
from app.model_runner import GenerationRequest


def test_ace_step_runner_submits_polls_and_downloads_wav(monkeypatch):
    calls = []

    class FakeRunner(AceStepHttpRunner):
        def _request(self, path, payload=None):
            calls.append((path, payload))
            if path == "/release_task":
                return {"code": 200, "data": {"task_id": "task-123"}}
            if path == "/query_result":
                return {"code": 200, "data": [{
                    "task_id": "task-123",
                    "status": 1,
                    "result": '[{"status": 1, "file": "/v1/audio?path=%2Ftmp%2Ftrack.wav", "metas": {"duration": 24}}]',
                }]}
            raise AssertionError(f"Unexpected request path: {path}")

    class FakeResponse:
        headers = {"Content-Type": "audio/wav"}

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def read(self):
            return b"RIFFfake-wav-data"

    monkeypatch.setattr("app.ace_step_runner.urlopen", lambda *args, **kwargs: FakeResponse())
    monkeypatch.setattr("app.ace_step_runner.time.sleep", lambda *_: None)
    monkeypatch.setattr("app.ace_step_runner.settings.default_generation_duration_seconds", 30)

    runner = FakeRunner(base_url="http://127.0.0.1:8001", timeout_seconds=5)
    result = runner.generate(GenerationRequest("Warm Afrobeats", "Afrobeats", True))

    assert result.data.startswith(b"RIFF")
    assert result.duration_seconds == 24
    assert result.suffix == ".wav"
    assert calls[0][0] == "/release_task"
    assert calls[0][1]["batch_size"] == 1
    assert calls[0][1]["audio_format"] == "wav"
    assert "no vocals" in calls[0][1]["prompt"].lower()
    assert calls[1][0] == "/query_result"


def test_ace_step_rejects_audio_url_from_another_host():
    class FakeRunner(AceStepHttpRunner):
        def _request(self, path, payload=None):
            if path == "/release_task":
                return {"data": {"task_id": "task-123"}}
            return {"data": [{
                "status": 1,
                "result": '[{"status": 1, "file": "https://attacker.invalid/audio.wav"}]',
            }]}

    runner = FakeRunner(base_url="http://127.0.0.1:8001", timeout_seconds=5)
    try:
        runner.generate(GenerationRequest("A song", None, False))
    except Exception as exc:
        assert "unexpected host" in str(exc).lower()
    else:
        raise AssertionError("Unexpected external audio URL should be rejected")



def test_ace_step_reports_generation_failure():
    class FakeRunner(AceStepHttpRunner):
        def _request(self, path, payload=None):
            if path == "/release_task":
                return {"data": {"task_id": "task-fail"}}
            return {"data": [{"task_id": "task-fail", "status": 2, "result": "[]"}]}

    runner = FakeRunner(base_url="http://127.0.0.1:8001", timeout_seconds=5)
    with pytest.raises(AceStepError, match="generation failed"):
        runner.generate(GenerationRequest("A song", None, False))


def test_ace_step_rejects_malformed_result_json():
    class FakeRunner(AceStepHttpRunner):
        def _request(self, path, payload=None):
            if path == "/release_task":
                return {"data": {"task_id": "task-bad-json"}}
            return {"data": [{
                "task_id": "task-bad-json",
                "status": 1,
                "result": "{not valid json",
            }]}

    runner = FakeRunner(base_url="http://127.0.0.1:8001", timeout_seconds=5)
    with pytest.raises(AceStepError, match="malformed generation results"):
        runner.generate(GenerationRequest("A song", None, False))


def test_ace_step_requires_positive_timeout():
    with pytest.raises(ValueError, match="at least 1 second"):
        AceStepHttpRunner(base_url="http://127.0.0.1:8001", timeout_seconds=0)

def test_ace_step_rejects_json_that_is_not_an_object(monkeypatch):
    class FakeResponse:
        headers = {"Content-Type": "application/json"}

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        def read(self):
            return b"[]"

    monkeypatch.setattr("app.ace_step_runner.urlopen", lambda *args, **kwargs: FakeResponse())
    runner = AceStepHttpRunner(base_url="http://127.0.0.1:8001", timeout_seconds=5)
    with pytest.raises(AceStepError, match="not an object"):
        runner._request("/release_task", {"prompt": "test"})
