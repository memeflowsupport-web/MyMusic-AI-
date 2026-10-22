from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class GenerationRequest:
    prompt: str
    style: str | None
    instrumental: bool


@dataclass(frozen=True)
class GeneratedAudio:
    data: bytes
    title: str
    duration_seconds: int
    suffix: str = ".wav"


class MusicModelRunner(Protocol):
    def generate(self, request: GenerationRequest) -> GeneratedAudio:
        """Generate real audio locally or raise an error."""
        ...


class ModelNotConfiguredError(RuntimeError):
    pass


class UnconfiguredMusicModel:
    """Default implementation refuses to fake output while no model is installed."""
    def generate(self, request: GenerationRequest) -> GeneratedAudio:
        raise ModelNotConfiguredError(
            "No local music model is configured yet. The generation engine is not connected."
        )
