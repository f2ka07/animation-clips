from providers.base import VideoProvider, VideoProviderError

import config


def create_video_provider() -> VideoProvider:
    """Return the configured video provider implementation."""
    config.validate_runtime_config()

    if config.PROVIDER == "aws":
        from providers.aws import AwsVideoProvider

        return AwsVideoProvider()

    if config.PROVIDER == "runpod":
        from providers.runpod import RunpodVideoProvider

        return RunpodVideoProvider()

    if config.PROVIDER == "minimax":
        from providers.minimax import MinimaxVideoProvider

        return MinimaxVideoProvider()

    raise VideoProviderError(
        f"Unsupported PROVIDER '{config.PROVIDER}'. Supported: aws, runpod, minimax"
    )


__all__ = [
    "VideoProvider",
    "VideoProviderError",
    "create_video_provider",
]
