import json
from pathlib import Path
from typing import Any

from rich.console import Console

import config
from providers._rest import RestVideoProvider, persist_video_output
from providers.base import VideoProvider, VideoProviderError

console = Console()


def validate_config() -> None:
    if config.AWS_MODE == "rest":
        if not config.API_HOST:
            raise RuntimeError("AWS_MODE=rest requires API_HOST in .env.")
        if config.API_PROTOCOL not in {"http", "https"}:
            raise RuntimeError(
                f"API_PROTOCOL '{config.API_PROTOCOL}' is not supported for REST. "
                "Use http or https."
            )
        return

    if config.AWS_MODE == "sagemaker":
        if not config.AWS_SAGEMAKER_ENDPOINT_NAME:
            raise RuntimeError(
                "AWS_MODE=sagemaker requires AWS_SAGEMAKER_ENDPOINT_NAME in .env."
            )
        if not config.AWS_REGION:
            raise RuntimeError("AWS_MODE=sagemaker requires AWS_REGION in .env.")
        return

    raise RuntimeError(
        f"Unsupported AWS_MODE '{config.AWS_MODE}'. Use 'rest' or 'sagemaker'."
    )


def _rest_base_url() -> str:
    return f"{config.API_PROTOCOL}://{config.API_HOST}:{config.API_PORT}"


def _rest_generate_url() -> str:
    return f"{_rest_base_url()}{config.API_GENERATE_PATH}"


def _rest_status_url(job_id: str) -> str:
    status_path = config.API_STATUS_PATH.rstrip("/")
    return f"{_rest_base_url()}{status_path}/{job_id}"


class AwsSagemakerVideoProvider(VideoProvider):
    def __init__(self) -> None:
        try:
            import boto3
        except ImportError as exc:
            raise VideoProviderError(
                "boto3 is required for AWS SageMaker. Install requirements.txt."
            ) from exc

        client_kwargs: dict[str, str] = {"region_name": config.AWS_REGION}
        if config.AWS_ACCESS_KEY_ID and config.AWS_SECRET_ACCESS_KEY:
            client_kwargs["aws_access_key_id"] = config.AWS_ACCESS_KEY_ID
            client_kwargs["aws_secret_access_key"] = config.AWS_SECRET_ACCESS_KEY
        if config.AWS_SESSION_TOKEN:
            client_kwargs["aws_session_token"] = config.AWS_SESSION_TOKEN

        self._client = boto3.client("sagemaker-runtime", **client_kwargs)

    def generate(self, payload: dict[str, Any]) -> dict[str, Any]:
        body = config.wrap_request_body(payload)
        console.print(
            "[cyan]Invoking SageMaker endpoint[/cyan] "
            f"{config.AWS_SAGEMAKER_ENDPOINT_NAME}"
        )
        response = self._client.invoke_endpoint(
            EndpointName=config.AWS_SAGEMAKER_ENDPOINT_NAME,
            ContentType="application/json",
            Body=json.dumps(body),
        )
        raw = response["Body"].read()
        data = json.loads(raw)
        output = data.get(config.OUTPUT_FIELD, data)
        if not isinstance(output, dict):
            raise VideoProviderError(
                f"Expected dict output from field '{config.OUTPUT_FIELD}': {data}"
            )
        return output

    def save_video(self, output: dict[str, Any], destination: Path) -> Path:
        return persist_video_output(output, destination)


class AwsVideoProvider(VideoProvider):
    def __init__(self) -> None:
        validate_config()
        if config.AWS_MODE == "sagemaker":
            self._impl: VideoProvider = AwsSagemakerVideoProvider()
        else:
            self._impl = RestVideoProvider(
                generate_url=_rest_generate_url(),
                status_url_for_job=_rest_status_url,
                auth_token=config.API_AUTH_TOKEN,
            )

    def generate(self, payload: dict[str, Any]) -> dict[str, Any]:
        return self._impl.generate(payload)

    def save_video(self, output: dict[str, Any], destination: Path) -> Path:
        return self._impl.save_video(output, destination)
