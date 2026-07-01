import base64
import json
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import requests
from rich.console import Console

import config
from providers.base import VideoProvider, VideoProviderError

console = Console()


class RunpodVideoProvider(VideoProvider):
    def __init__(
        self,
        poll_interval: float | None = None,
        timeout: float | None = None,
    ) -> None:
        self.poll_interval = (
            config.POLL_INTERVAL if poll_interval is None else poll_interval
        )
        self.timeout = config.TIMEOUT if timeout is None else timeout
        self._session = requests.Session()
        headers = {"Content-Type": "application/json"}
        if config.USE_AUTH_HEADER and config.RUNPOD_API_KEY:
            prefix = config.AUTH_HEADER_PREFIX.strip()
            token = config.RUNPOD_API_KEY
            value = f"{prefix} {token}".strip() if prefix else token
            headers[config.AUTH_HEADER_NAME] = value
        self._session.headers.update(headers)

    def _submit_job(self, payload: dict[str, Any]) -> str:
        body = config.wrap_request_body(payload)
        url = config.build_generate_url()
        response = self._session.post(url, json=body, timeout=60)
        response.raise_for_status()
        data = response.json()

        if not config.POLLING_ENABLED:
            return ""

        job_id = data.get(config.JOB_ID_FIELD)
        if not job_id:
            raise VideoProviderError(
                f"API did not return job id in field '{config.JOB_ID_FIELD}': {data}"
            )
        console.print(f"[cyan]Submitted job[/cyan] {job_id}")
        return str(job_id)

    def _poll_until_complete(self, job_id: str) -> dict[str, Any]:
        deadline = time.monotonic() + self.timeout
        pending_statuses = {
            config.STATUS_IN_QUEUE,
            config.STATUS_IN_PROGRESS,
        }

        while time.monotonic() < deadline:
            url = config.build_status_url(job_id)
            response = self._session.get(url, timeout=60)
            response.raise_for_status()
            data = response.json()
            status = data.get(config.STATUS_FIELD, "UNKNOWN")
            console.print(
                f"[dim]Job {job_id}[/dim] status: [bold]{status}[/bold]"
            )

            if status == config.STATUS_COMPLETED:
                return data
            if status == config.STATUS_FAILED:
                error = (
                    data.get(config.ERROR_FIELD)
                    or data.get(config.OUTPUT_FIELD)
                    or data
                )
                raise VideoProviderError(f"Generation job failed: {error}")
            if status in pending_statuses:
                time.sleep(self.poll_interval)
                continue

            raise VideoProviderError(f"Unexpected status '{status}': {data}")

        raise VideoProviderError(
            f"Job {job_id} timed out after {int(self.timeout)} seconds"
        )

    def generate(self, payload: dict[str, Any]) -> dict[str, Any]:
        url = config.build_generate_url()
        body = config.wrap_request_body(payload)

        if not config.POLLING_ENABLED:
            response = self._session.post(url, json=body, timeout=int(self.timeout))
            response.raise_for_status()
            data = response.json()
            output = data.get(config.OUTPUT_FIELD, data)
            if not isinstance(output, dict):
                raise VideoProviderError(
                    f"Expected dict output from field '{config.OUTPUT_FIELD}': {data}"
                )
            return output

        job_id = self._submit_job(payload)
        result = self._poll_until_complete(job_id)
        output = result.get(config.OUTPUT_FIELD)
        if output is None:
            raise VideoProviderError(
                f"Completed job has no '{config.OUTPUT_FIELD}': {result}"
            )
        if not isinstance(output, dict):
            raise VideoProviderError(
                f"Expected dict in '{config.OUTPUT_FIELD}', got: {type(output).__name__}"
            )
        return output

    def save_video(self, output: dict[str, Any], destination: Path) -> Path:
        destination.parent.mkdir(parents=True, exist_ok=True)

        video_url = output.get(config.VIDEO_URL_FIELD)
        if video_url:
            console.print("[cyan]Downloading video from URL[/cyan]")
            response = requests.get(str(video_url), timeout=300)
            response.raise_for_status()
            destination.write_bytes(response.content)
            return destination

        video_base64 = output.get(config.VIDEO_BASE64_FIELD)
        if video_base64:
            console.print("[cyan]Decoding base64 video[/cyan]")
            destination.write_bytes(base64.b64decode(str(video_base64)))
            return destination

        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        failed_path = config.LOGS_DIR / f"failed_response_{timestamp}.json"
        failed_path.parent.mkdir(parents=True, exist_ok=True)
        failed_path.write_text(json.dumps(output, indent=2), encoding="utf-8")
        raise VideoProviderError(
            "No video found in output fields "
            f"'{config.VIDEO_URL_FIELD}' or '{config.VIDEO_BASE64_FIELD}'. "
            f"Full response saved to {failed_path}"
        )
