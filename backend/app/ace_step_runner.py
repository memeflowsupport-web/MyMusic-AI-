"""ACE-Step 1.5 HTTP adapter using its documented asynchronous REST API.

The model runs as a separate, self-hosted service. This adapter never downloads
or installs model weights inside the API process.
"""
from __future__ import annotations

import json
import time
from urllib.error import HTTPError, URLError
from urllib.parse import urljoin, urlparse
from urllib.request import Request, urlopen

from app.config import settings
from app.model_runner import (
    GeneratedAudio,
    GenerationRequest,
    ModelNotConfiguredError,
)


class AceStepError(RuntimeError):
    """ACE-Step service or response error."""


class AceStepHttpRunner:
    def __init__(
        self,
        base_url: str | None = None,
        api_key: str | None = None,
        timeout_seconds: int | None = None,
        poll_seconds: float | None = None,
    ) -> None:
        self.base_url = (base_url or settings.ace_step_base_url).rstrip("/") + "/"
        self.api_key = api_key if api_key is not None else settings.ace_step_api_key
        self.timeout_seconds = timeout_seconds or settings.ace_step_timeout_seconds
        self.poll_seconds = poll_seconds or settings.ace_step_poll_seconds
        if self.timeout_seconds < 1:
            raise ValueError("ACE_STEP_TIMEOUT_SECONDS must be at least 1 second.")
        self._deadline: float | None = None
        if not self.base_url.startswith(("http://", "https://")):
            raise ValueError("ACE_STEP_BASE_URL must be an HTTP(S) URL.")

    def _request(self, path: str, payload: dict | None = None) -> dict | bytes:
        headers = {"Accept": "application/json"}
        data = None
        if payload is not None:
            data = json.dumps(payload).encode("utf-8")
            headers["Content-Type"] = "application/json"
        if self.api_key:
            headers["Authorization"] = f"Bearer {self.api_key}"
        req = Request(urljoin(self.base_url, path.lstrip("/")), data=data, headers=headers)
        remaining = self.timeout_seconds if self._deadline is None else self._deadline - time.monotonic()
        if remaining <= 0:
            raise AceStepError("Timed out waiting for ACE-Step generation.")
        try:
            with urlopen(req, timeout=min(60, remaining)) as response:
                body = response.read()
                content_type = response.headers.get("Content-Type", "")
        except (HTTPError, URLError, TimeoutError) as exc:
            raise AceStepError(f"ACE-Step request failed: {exc}") from exc
        if "application/json" in content_type or path in ("/release_task", "/query_result"):
            try:
                result = json.loads(body.decode("utf-8"))
            except (UnicodeDecodeError, json.JSONDecodeError) as exc:
                raise AceStepError("ACE-Step returned invalid JSON.") from exc
            if result.get("code", 200) != 200 or result.get("error"):
                raise AceStepError(str(result.get("error") or "ACE-Step rejected the request."))
            return result
        return body

    def generate(self, request: GenerationRequest) -> GeneratedAudio:
        if not request.prompt.strip():
            raise ValueError("A non-empty music prompt is required.")
        self._deadline = time.monotonic() + self.timeout_seconds
        duration = max(10, min(600, int(settings.default_generation_duration_seconds)))
        prompt = request.prompt.strip()
        if request.style and request.style.strip():
            prompt = f"{prompt}. Style: {request.style.strip()}."
        if request.instrumental:
            prompt += " Instrumental music only; no vocals or lyrics."

        submitted = self._request("/release_task", {
            "prompt": prompt,
            "lyrics": "",
            "thinking": True,
            "audio_duration": duration,
            "audio_format": "wav",
            "task_type": "text2music",
            "batch_size": 1,
        })
        task_id = (submitted.get("data") or {}).get("task_id")
        if not task_id:
            raise AceStepError("ACE-Step did not return a task ID.")

        result_items = None
        while time.monotonic() < self._deadline:
            response = self._request("/query_result", {"task_id_list": [task_id]})
            data = response.get("data")
            if isinstance(data, list) and data:
                item = data[0]
                status = item.get("status", 0)
                if status == 2:
                    raise AceStepError("ACE-Step reported that generation failed.")
                if status == 1:
                    raw_result = item.get("result", "[]")
                    try:
                        result_items = json.loads(raw_result) if isinstance(raw_result, str) else raw_result
                    except json.JSONDecodeError as exc:
                        raise AceStepError("ACE-Step returned malformed generation results.") from exc
                    break
            time.sleep(max(0.25, self.poll_seconds))
        else:
            raise AceStepError("Timed out waiting for ACE-Step generation.")

        if not isinstance(result_items, list) or not result_items:
            raise AceStepError("ACE-Step completed without an audio file.")
        audio_item = next((item for item in result_items if item.get("status", 1) == 1 and item.get("file")), None)
        if not audio_item:
            raise AceStepError("ACE-Step result did not include a successful audio file.")
        file_ref = str(audio_item["file"])
        parsed = urlparse(file_ref)
        if parsed.scheme and parsed.netloc:
            # Never send the configured API key to a different host.
            if (parsed.scheme, parsed.netloc) != (urlparse(self.base_url).scheme, urlparse(self.base_url).netloc):
                raise AceStepError("ACE-Step returned an audio URL on an unexpected host.")
            audio_url = file_ref
        elif file_ref.startswith("/v1/audio?"):
            audio_url = urljoin(self.base_url, file_ref.lstrip("/"))
        else:
            raise AceStepError("ACE-Step returned an unsupported audio URL.")
        audio_req = Request(audio_url, headers={"Accept": "audio/wav"})
        if self.api_key:
            audio_req.add_header("Authorization", f"Bearer {self.api_key}")
        try:
            remaining = self._deadline - time.monotonic()
            if remaining <= 0:
                raise AceStepError("Timed out before generated audio could be downloaded.")
            with urlopen(audio_req, timeout=min(60, remaining)) as response:
                audio_data = response.read()
        except (HTTPError, URLError, TimeoutError) as exc:
            raise AceStepError(f"Could not download generated audio: {exc}") from exc
        if not audio_data:
            raise AceStepError("ACE-Step audio download was empty.")
        self._deadline = None
        metadata = audio_item.get("metas") or {}
        actual_duration = metadata.get("duration") or duration
        return GeneratedAudio(
            data=audio_data,
            title=(request.prompt.strip()[:180] or "Generated track"),
            duration_seconds=max(1, int(float(actual_duration))),
            suffix=".wav",
        )


def build_music_runner():
    """Select a runner explicitly; never silently fake generated audio."""
    backend = settings.music_model_backend.strip().lower()
    if backend == "ace_step":
        return AceStepHttpRunner()
    if backend == "unconfigured":
        from app.model_runner import UnconfiguredMusicModel
        return UnconfiguredMusicModel()
    raise ModelNotConfiguredError(
        f"Unsupported MUSIC_MODEL_BACKEND '{backend}'. Use 'unconfigured' or 'ace_step'."
    )
