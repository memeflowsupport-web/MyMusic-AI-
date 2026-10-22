from pathlib import Path
from uuid import uuid4

from app.config import settings


class LocalAudioStorage:
    """Development-only storage using opaque keys, never caller paths."""

    def __init__(self, root: str | Path | None = None) -> None:
        self.root = Path(root or settings.audio_storage_dir).expanduser().resolve()
        self.root.mkdir(parents=True, exist_ok=True)

    def save(self, data: bytes, suffix: str = ".wav") -> str:
        if not suffix.startswith(".") or len(suffix) > 8 or not suffix[1:].isalnum():
            raise ValueError("Unsupported audio file suffix")
        key = f"{uuid4().hex}{suffix.lower()}"
        destination = (self.root / key).resolve()
        if destination.parent != self.root:
            raise ValueError("Invalid storage key")
        destination.write_bytes(data)
        return key

    def path_for_read(self, key: str) -> Path:
        """Resolve a stored object safely; callers must never supply filesystem paths."""
        if not key or Path(key).name != key or key in {".", ".."}:
            raise ValueError("Invalid storage key")
        path = (self.root / key).resolve()
        if path.parent != self.root or not path.is_file():
            raise FileNotFoundError("Audio object not found")
        return path

    def read(self, key: str) -> bytes:
        return self.path_for_read(key).read_bytes()

    def delete(self, key: str) -> None:
        if not key or Path(key).name != key or key in {".", ".."}:
            raise ValueError("Invalid storage key")
        path = (self.root / key).resolve()
        if path.parent != self.root:
            raise ValueError("Invalid storage key")
        path.unlink(missing_ok=True)
