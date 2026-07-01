"""RunPod serverless submit/poll/download for any endpoint."""

from __future__ import annotations

import base64
import json
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import requests
from rich.console import Console

import config
from providers.base import VideoProviderError

console = Console()


def _auth_headers() -> dict[str, str]:
    token = config.RUNPOD_API_KEY or config.API_AUTH_TOKEN
    if not token:
        raise VideoProviderError(
            "RUNPOD_API_KEY is missing. Set it in D:\\VideoApp\\.env or wan-stick-clips\\.env."
        )
    headers = {"Content-Type": "application/json"}
    if config.USE_AUTH_HEADER:
        prefix = config.AUTH_HEADER_PREFIX.strip()
        value = f"{prefix} {token}".strip() if prefix else token
        headers[config.AUTH_HEADER_NAME] = value
    return headers


def _generate_url(endpoint_id: str) -> str:
    return f"{config.SERVERLESS_BASE_URL}/{endpoint_id}{config.API_GENERATE_PATH}"


def _status_url(endpoint_id: str, job_id: str) -> str:
    status_path = config.API_STATUS_PATH.rstrip("/")
    return f"{config.SERVERLESS_BASE_URL}/{endpoint_id}{status_path}/{job_id}"


def submit_job(endpoint_id: str, input_payload: dict[str, Any]) -> str:
    body = config.wrap_request_body(input_payload)
    response = requests.post(
        _generate_url(endpoint_id),
        headers=_auth_headers(),
        json=body,
        timeout=60,
    )
    response.raise_for_status()
    data = response.json()
    job_id = data.get(config.JOB_ID_FIELD)
    if not job_id:
        raise VideoProviderError(
            f"RunPod did not return job id in '{config.JOB_ID_FIELD}': {data}"
        )
    console.print(f"[cyan]Submitted job[/cyan] {job_id} -> {endpoint_id}")
    return str(job_id)


def poll_job(endpoint_id: str, job_id: str) -> dict[str, Any]:
    deadline = time.monotonic() + config.TIMEOUT
    pending = {config.STATUS_IN_QUEUE, config.STATUS_IN_PROGRESS}

    while time.monotonic() < deadline:
        response = requests.get(
            _status_url(endpoint_id, job_id),
            headers=_auth_headers(),
            timeout=60,
        )
        response.raise_for_status()
        data = response.json()
        status = data.get(config.STATUS_FIELD, "UNKNOWN")
        console.print(f"[dim]Job {job_id}[/dim] status: [bold]{status}[/bold]")

        if status == config.STATUS_COMPLETED:
            output = data.get(config.OUTPUT_FIELD)
            if output is None:
                raise VideoProviderError(
                    f"Completed job has no '{config.OUTPUT_FIELD}': {data}"
                )
            if isinstance(output, dict):
                return output
            if isinstance(output, str):
                return {config.IMAGE_URL_FIELD: output}
            raise VideoProviderError(f"Unexpected output type: {type(output).__name__}")

        if status == config.STATUS_FAILED:
            error = data.get(config.ERROR_FIELD) or data.get(config.OUTPUT_FIELD) or data
            raise VideoProviderError(f"RunPod job failed: {error}")

        if status in pending:
            time.sleep(config.POLL_INTERVAL)
            continue

        raise VideoProviderError(f"Unexpected status '{status}': {data}")

    raise VideoProviderError(
        f"Job {job_id} timed out after {int(config.TIMEOUT)} seconds"
    )


def run_job(endpoint_id: str, input_payload: dict[str, Any]) -> dict[str, Any]:
    job_id = submit_job(endpoint_id, input_payload)
    return poll_job(endpoint_id, job_id)


def _first_url(output: dict[str, Any], *fields: str) -> str | None:
    for field in fields:
        value = output.get(field)
        if isinstance(value, str) and value.strip():
            if value.startswith("http://") or value.startswith("https://"):
                return value.strip()
    return None


def extract_media_url(output: dict[str, Any]) -> str:
    url = _first_url(
        output,
        config.VIDEO_URL_FIELD,
        config.IMAGE_URL_FIELD,
        "result",
        "video_url",
        "image_url",
        "url",
        "output",
    )
    if url:
        return url

    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    failed_path = config.LOGS_DIR / f"failed_response_{timestamp}.json"
    failed_path.parent.mkdir(parents=True, exist_ok=True)
    failed_path.write_text(json.dumps(output, indent=2), encoding="utf-8")
    raise VideoProviderError(
        "No media URL found in RunPod output. "
        f"Checked video/image/result fields. Full response: {failed_path}"
    )


def download_url(url: str, destination: Path) -> Path:
    destination.parent.mkdir(parents=True, exist_ok=True)
    console.print(f"[cyan]Downloading[/cyan] {url}")
    response = requests.get(url, timeout=300)
    response.raise_for_status()
    destination.write_bytes(response.content)
    return destination


def save_media(output: dict[str, Any], destination: Path) -> Path:
    destination.parent.mkdir(parents=True, exist_ok=True)

    for field in (config.VIDEO_BASE64_FIELD, config.IMAGE_BASE64_FIELD, "image_base64"):
        encoded = output.get(field)
        if encoded:
            destination.write_bytes(base64.b64decode(str(encoded)))
            return destination

    return download_url(extract_media_url(output), destination)
