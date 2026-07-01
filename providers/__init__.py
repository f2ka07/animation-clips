from providers.base import VideoProvider, VideoProviderError

import config


def create_video_provider() -> VideoProvider:
    """Return the configured video provider implementation."""
    config.validate_runtime_config()

    if config.PROVIDER == "runpod":
        from providers.runpod import RunpodVideoProvider

        return RunpodVideoProvider()

    raise VideoProviderError(
        f"Unsupported PROVIDER '{config.PROVIDER}'. Supported: runpod"
    )


__all__ = [
    "VideoProvider",
    "VideoProviderError",
    "create_video_provider",
]
