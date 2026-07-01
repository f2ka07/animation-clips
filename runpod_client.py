"""Backward-compatible shim. Prefer providers.create_video_provider()."""

from providers import VideoProviderError, create_video_provider
from providers.runpod import RunpodVideoProvider

RunpodError = VideoProviderError
RunpodClient = RunpodVideoProvider

__all__ = ["RunpodClient", "RunpodError", "RunpodVideoProvider", "create_video_provider"]
