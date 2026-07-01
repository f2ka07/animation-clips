from providers.base import VideoProvider, VideoProviderError
from providers.runpod import RunpodVideoProvider

import config

_SUPPORTED_PROVIDERS = {
    "runpod": RunpodVideoProvider,
}


def create_video_provider() -> VideoProvider:
    """Return the configured video provider implementation."""
    config.validate_runtime_config()
    provider_cls = _SUPPORTED_PROVIDERS.get(config.PROVIDER)
    if provider_cls is None:
        supported = ", ".join(sorted(_SUPPORTED_PROVIDERS))
        raise VideoProviderError(
            f"Unsupported PROVIDER '{config.PROVIDER}'. Supported: {supported}"
        )
    return provider_cls()


__all__ = [
    "VideoProvider",
    "VideoProviderError",
    "RunpodVideoProvider",
    "create_video_provider",
]
