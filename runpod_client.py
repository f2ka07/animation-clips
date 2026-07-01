import base64
import json
import time
from datetime import datetime, timezone
from pathlib import Path

import requests
from rich.console import Console

import config

console = Console()


class RunpodError(Exception):
    pass


class RunpodClient:
    def __init__(
        self,
        api_key: str | None = None,
        endpoint_id: str | None = None,
        poll_interval: float = config.POLL_INTERVAL_SECONDS,
        timeout: float = config.JOB_TIMEOUT_SECONDS,
    ) -> None:
        self.api_key = api_key or config.get_runpod_api_key()
        self.endpoint_id = endpoint_id or config.get_runpod_endpoint_id()
        self.poll_interval = poll_interval
        self.timeout = timeout
        self._session = requests.Session()
        self._session.headers.update(
            {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            }
        )

    def _run_url(self) -> str:
        return f"https://api.runpod.ai/v2/{self.endpoint_id}/run"

    def _status_url(self, job_id: str) -> str:
        return f"https://api.runpod.ai/v2/{self.endpoint_id}/status/{job_id}"

    def submit_job(self, payload: dict[str, Any]) -> str:
        response = self._session.post(self._run_url(), json=payload, timeout=60)
        response.raise_for_status()
        data = response.json()
        job_id = data.get("id")
        if not job_id:
            raise RunpodError(f"Runpod did not return a job id: {data}")
        console.print(f"[cyan]Submitted job[/cyan] {job_id}")
        return job_id

    def poll_until_complete(self, job_id: str) -> dict[str, Any]:
        deadline = time.monotonic() + self.timeout
        while time.monotonic() < deadline:
            response = self._session.get(self._status_url(job_id), timeout=60)
            response.raise_for_status()
            data = response.json()
            status = data.get("status", "UNKNOWN")
            console.print(f"[dim]Job {job_id}[/dim] status: [bold]{status}[/bold]")

            if status == "COMPLETED":
                return data
            if status == "FAILED":
                error = data.get("error") or data.get("output") or data
                raise RunpodError(f"Runpod job failed: {error}")
            if status in ("IN_QUEUE", "IN_PROGRESS"):
                time.sleep(self.poll_interval)
                continue

            raise RunpodError(f"Unexpected Runpod status '{status}': {data}")

        raise RunpodError(
            f"Runpod job {job_id} timed out after {int(self.timeout)} seconds"
        )

    def run(self, input_payload: dict[str, Any]) -> dict[str, Any]:
        job_id = self.submit_job({"input": input_payload})
        result = self.poll_until_complete(job_id)
        output = result.get("output")
        if output is None:
            raise RunpodError(f"Completed job has no output: {result}")
        return output

    def save_video_output(
        self, output: dict[str, Any], destination: Path
    ) -> Path:
        destination.parent.mkdir(parents=True, exist_ok=True)

        video_url = output.get("video_url")
        if video_url:
            console.print("[cyan]Downloading video from URL[/cyan]")
            response = requests.get(video_url, timeout=300)
            response.raise_for_status()
            destination.write_bytes(response.content)
            return destination

        video_base64 = output.get("video_base64")
        if video_base64:
            console.print("[cyan]Decoding base64 video[/cyan]")
            destination.write_bytes(base64.b64decode(video_base64))
            return destination

        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        failed_path = config.LOGS_DIR / f"failed_response_{timestamp}.json"
        failed_path.parent.mkdir(parents=True, exist_ok=True)
        failed_path.write_text(json.dumps(output, indent=2), encoding="utf-8")
        raise RunpodError(
            f"No video_url or video_base64 in output. Full response saved to {failed_path}"
        )
