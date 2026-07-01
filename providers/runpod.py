import json
from pathlib import Path
from typing import Any

import config
from providers._rest import RestVideoProvider
from providers.base import VideoProvider


def validate_config() -> None:
    if config.RUNPOD_MODE == "pod":
        if not config.API_HOST:
            raise RuntimeError("RUNPOD_MODE=pod requires API_HOST in .env.")
        if config.API_PROTOCOL not in {"http", "https"}:
            raise RuntimeError(
                f"API_PROTOCOL '{config.API_PROTOCOL}' is not supported for REST. "
                "Use http or https."
            )
        return

    if config.RUNPOD_MODE == "serverless":
        token = config.RUNPOD_API_KEY or config.API_AUTH_TOKEN
        if not token:
            raise RuntimeError(
                "RUNPOD_MODE=serverless requires RUNPOD_API_KEY or API_AUTH_TOKEN."
            )
        if not config.RUNPOD_ENDPOINT_ID:
            raise RuntimeError(
                "RUNPOD_MODE=serverless requires RUNPOD_ENDPOINT_ID in .env."
            )
        return

    raise RuntimeError(
        f"Unsupported RUNPOD_MODE '{config.RUNPOD_MODE}'. Use 'pod' or 'serverless'."
    )


def _pod_base_url() -> str:
    return f"{config.API_PROTOCOL}://{config.API_HOST}:{config.API_PORT}"


def _pod_generate_url() -> str:
    return f"{_pod_base_url()}{config.API_GENERATE_PATH}"


def _pod_status_url(job_id: str) -> str:
    status_path = config.API_STATUS_PATH.rstrip("/")
    return f"{_pod_base_url()}{status_path}/{job_id}"


def _serverless_generate_url() -> str:
    return (
        f"{config.SERVERLESS_BASE_URL}/{config.RUNPOD_ENDPOINT_ID}"
        f"{config.API_GENERATE_PATH}"
    )


def _serverless_status_url(job_id: str) -> str:
    status_path = config.API_STATUS_PATH.rstrip("/")
    return (
        f"{config.SERVERLESS_BASE_URL}/{config.RUNPOD_ENDPOINT_ID}"
        f"{status_path}/{job_id}"
    )


class RunpodVideoProvider(VideoProvider):
    def __init__(self) -> None:
        validate_config()
        token = config.RUNPOD_API_KEY or config.API_AUTH_TOKEN
        if config.RUNPOD_MODE == "serverless":
            self._client = RestVideoProvider(
                generate_url=_serverless_generate_url(),
                status_url_for_job=_serverless_status_url,
                auth_token=token,
            )
        else:
            self._client = RestVideoProvider(
                generate_url=_pod_generate_url(),
                status_url_for_job=_pod_status_url,
                auth_token=token,
            )

    def generate(self, payload: dict[str, Any]) -> dict[str, Any]:
        return self._client.generate(payload)

    def save_video(self, output: dict[str, Any], destination: Path) -> Path:
        return self._client.save_video(output, destination)
