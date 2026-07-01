from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any


class VideoProviderError(Exception):
    pass


class VideoProvider(ABC):
    @abstractmethod
    def generate(self, payload: dict[str, Any]) -> dict[str, Any]:
        """Submit a generation job and return the provider output dict."""

    @abstractmethod
    def save_video(self, output: dict[str, Any], destination: Path) -> Path:
        """Persist video bytes from a provider output dict."""
