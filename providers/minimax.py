import time
from pathlib import Path
from typing import Any

import requests
from rich.console import Console

import config
from providers._rest import persist_video_output
from providers.base import VideoProvider, VideoProviderError

console = Console()


def validate_config() -> None:
    if not config.MINIMAX_API_KEY:
        raise RuntimeError("PROVIDER=minimax requires MINIMAX_API_KEY in .env.")


def _headers() -> dict[str, str]:
    return {
        "Authorization": f"Bearer {config.MINIMAX_API_KEY}",
        "Content-Type": "application/json",
    }


def _check_base_response(data: dict[str, Any]) -> None:
    base_resp = data.get("base_resp", {})
    code = base_resp.get("status_code", 0)
    if code != 0:
        message = base_resp.get("status_msg", "Unknown MiniMax API error")
        raise VideoProviderError(f"MiniMax API error [{code}]: {message}")


def _nested_get(data: dict[str, Any], dotted_path: str) -> Any:
    current: Any = data
    for part in dotted_path.split("."):
        if not isinstance(current, dict) or part not in current:
            return None
        current = current[part]
    return current


def _payload_value(payload: dict[str, Any], field_name: str, default: Any = None) -> Any:
    return payload.get(field_name, default)


def _minimax_duration(duration_seconds: int) -> int:
    # MiniMax Hailuo models commonly support 6s or 10s clips.
    if duration_seconds <= 6:
        return 6
    return 10


def _minimax_resolution(width: int, height: int) -> str:
    if config.MINIMAX_RESOLUTION:
        return config.MINIMAX_RESOLUTION
    if height >= 1000 or width >= 1920:
        return "1080P"
    if height >= 700 or width >= 1200:
        return "768P"
    return "720P"


def _build_minimax_request(payload: dict[str, Any]) -> dict[str, Any]:
    prompt = str(_payload_value(payload, config.PROMPT_FIELD, "")).strip()
    if not prompt:
        raise VideoProviderError(f"Missing '{config.PROMPT_FIELD}' in generation payload.")

    width = int(_payload_value(payload, config.WIDTH_FIELD, config.WIDTH))
    height = int(_payload_value(payload, config.HEIGHT_FIELD, config.HEIGHT))
    duration = int(
        _payload_value(payload, config.DURATION_FIELD, config.DURATION)
    )

    return {
        "model": config.MINIMAX_MODEL,
        "prompt": prompt,
        "duration": _minimax_duration(duration),
        "resolution": _minimax_resolution(width, height),
        "prompt_optimizer": config.MINIMAX_PROMPT_OPTIMIZER,
    }


class MinimaxVideoProvider(VideoProvider):
    def __init__(self) -> None:
        validate_config()
        self._session = requests.Session()

    def _create_task(self, request_body: dict[str, Any]) -> str:
        url = f"{config.MINIMAX_API_BASE}{config.MINIMAX_GENERATE_PATH}"
        response = self._session.post(
            url, headers=_headers(), json=request_body, timeout=60
        )
        response.raise_for_status()
        data = response.json()
        _check_base_response(data)

        task_id = data.get(config.MINIMAX_TASK_ID_FIELD)
        if not task_id:
            raise VideoProviderError(
                f"MiniMax did not return '{config.MINIMAX_TASK_ID_FIELD}': {data}"
            )
        console.print(f"[cyan]Submitted MiniMax task[/cyan] {task_id}")
        return str(task_id)

    def _poll_task(self, task_id: str) -> str:
        url = f"{config.MINIMAX_API_BASE}{config.MINIMAX_QUERY_PATH}"
        deadline = time.monotonic() + config.TIMEOUT

        while time.monotonic() < deadline:
            response = self._session.get(
                url,
                headers=_headers(),
                params={"task_id": task_id},
                timeout=60,
            )
            response.raise_for_status()
            data = response.json()
            _check_base_response(data)

            status = str(data.get(config.STATUS_FIELD, ""))
            console.print(
                f"[dim]MiniMax task {task_id}[/dim] status: [bold]{status}[/bold]"
            )

            if status == config.MINIMAX_STATUS_SUCCESS:
                file_id = data.get(config.MINIMAX_FILE_ID_FIELD)
                if not file_id:
                    raise VideoProviderError(
                        f"MiniMax task succeeded but '{config.MINIMAX_FILE_ID_FIELD}' "
                        f"is missing: {data}"
                    )
                return str(file_id)

            if status == config.MINIMAX_STATUS_FAILED:
                error = data.get(config.ERROR_FIELD) or data
                raise VideoProviderError(f"MiniMax generation failed: {error}")

            time.sleep(config.POLL_INTERVAL)

        raise VideoProviderError(
            f"MiniMax task {task_id} timed out after {int(config.TIMEOUT)} seconds"
        )

    def _retrieve_download_url(self, file_id: str) -> str:
        url = f"{config.MINIMAX_API_BASE}{config.MINIMAX_FILE_PATH}"
        response = self._session.get(
            url,
            headers=_headers(),
            params={"file_id": file_id},
            timeout=60,
        )
        response.raise_for_status()
        data = response.json()
        _check_base_response(data)

        download_url = _nested_get(data, config.MINIMAX_DOWNLOAD_URL_FIELD)
        if not download_url:
            raise VideoProviderError(
                f"MiniMax file response missing '{config.MINIMAX_DOWNLOAD_URL_FIELD}': "
                f"{data}"
            )
        return str(download_url)

    def generate(self, payload: dict[str, Any]) -> dict[str, Any]:
        request_body = _build_minimax_request(payload)
        task_id = self._create_task(request_body)
        file_id = self._poll_task(task_id)
        download_url = self._retrieve_download_url(file_id)
        return {config.VIDEO_URL_FIELD: download_url}

    def save_video(self, output: dict[str, Any], destination: Path) -> Path:
        return persist_video_output(output, destination)
