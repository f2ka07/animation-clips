from pathlib import Path

from dotenv import load_dotenv
import os
import re

_BASE_DIR = Path(__file__).resolve().parent

load_dotenv(_BASE_DIR / ".env")
load_dotenv(_BASE_DIR.parent / ".env", override=False)


def _require(name: str) -> str:
    value = os.getenv(name)
    if value is None or value.strip() == "":
        raise RuntimeError(
            f"Missing required environment variable: {name}. "
            f"Copy .env.example to .env and set {name}."
        )
    return value.strip()


def _str_env(name: str, default: str = "") -> str:
    value = os.getenv(name)
    if value is None or value.strip() == "":
        return default
    return value.strip()


def _int_env(name: str, default: int) -> int:
    raw = os.getenv(name)
    if raw is None or raw.strip() == "":
        return default
    return int(raw)


def _float_env(name: str, default: float) -> float:
    raw = os.getenv(name)
    if raw is None or raw.strip() == "":
        return default
    return float(raw)


def _bool_env(name: str, default: bool) -> bool:
    raw = os.getenv(name)
    if raw is None or raw.strip() == "":
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


# Provider and connection
PROVIDER: str = _str_env("PROVIDER", "aws").lower()

# Generic API host (EC2, ALB, API Gateway, Runpod pod)
API_PROTOCOL: str = _str_env(
    "API_PROTOCOL", _str_env("POD_SCHEME", "http")
).lower()
API_HOST: str = _str_env("API_HOST", _str_env("POD_HOST", ""))
API_PORT: int = _int_env("API_PORT", _int_env("POD_PORT", 8000))
API_AUTH_TOKEN: str = _str_env("API_AUTH_TOKEN")

# AWS
AWS_MODE: str = _str_env("AWS_MODE", "rest").lower()
AWS_REGION: str = _str_env("AWS_REGION", "us-east-1")
AWS_ACCESS_KEY_ID: str = _str_env("AWS_ACCESS_KEY_ID")
AWS_SECRET_ACCESS_KEY: str = _str_env("AWS_SECRET_ACCESS_KEY")
AWS_SESSION_TOKEN: str = _str_env("AWS_SESSION_TOKEN")
AWS_SAGEMAKER_ENDPOINT_NAME: str = _str_env("AWS_SAGEMAKER_ENDPOINT_NAME")

# MiniMax
MINIMAX_API_KEY: str = _str_env("MINIMAX_API_KEY")
MINIMAX_API_BASE: str = _str_env(
    "MINIMAX_API_BASE", "https://api.minimax.io/v1"
).rstrip("/")
MINIMAX_MODEL: str = _str_env("MINIMAX_MODEL", "MiniMax-Hailuo-2.3")
MINIMAX_RESOLUTION: str = _str_env("MINIMAX_RESOLUTION", "")
MINIMAX_PROMPT_OPTIMIZER: bool = _bool_env("MINIMAX_PROMPT_OPTIMIZER", True)
MINIMAX_GENERATE_PATH: str = _str_env("MINIMAX_GENERATE_PATH", "/video_generation")
MINIMAX_QUERY_PATH: str = _str_env("MINIMAX_QUERY_PATH", "/query/video_generation")
MINIMAX_FILE_PATH: str = _str_env("MINIMAX_FILE_PATH", "/files/retrieve")
MINIMAX_STATUS_SUCCESS: str = _str_env("MINIMAX_STATUS_SUCCESS", "Success")
MINIMAX_STATUS_FAILED: str = _str_env("MINIMAX_STATUS_FAILED", "Fail")
MINIMAX_TASK_ID_FIELD: str = _str_env("MINIMAX_TASK_ID_FIELD", "task_id")
MINIMAX_FILE_ID_FIELD: str = _str_env("MINIMAX_FILE_ID_FIELD", "file_id")
MINIMAX_DOWNLOAD_URL_FIELD: str = _str_env(
    "MINIMAX_DOWNLOAD_URL_FIELD", "file.download_url"
)

# RunPod (legacy provider)
RUNPOD_API_KEY: str = _str_env("RUNPOD_API_KEY")
RUNPOD_MODE: str = _str_env("RUNPOD_MODE", "serverless").lower()
RUNPOD_ENDPOINT_ID: str = _str_env("RUNPOD_ENDPOINT_ID")
RUNPOD_T2V_ENDPOINT_ID: str = _str_env(
    "RUNPOD_T2V_ENDPOINT_ID", _str_env("RUNPOD_ENDPOINT_ID", "minimax-hailuo-02-std")
)
RUNPOD_T2I_ENDPOINT_ID: str = _str_env(
    "RUNPOD_T2I_ENDPOINT_ID",
    _str_env("RUNPOD_ENDPOINT_FLUX", "seedream-v4-t2i"),
)
RUNPOD_I2V_ENDPOINT_ID: str = _str_env(
    "RUNPOD_I2V_ENDPOINT_ID", "kling-v2-1-i2v-pro"
)
RUNPOD_PAYLOAD_PROFILE: str = _str_env("RUNPOD_PAYLOAD_PROFILE", "wan").lower()
MINIMAX_HAILUO_ENABLE_PROMPT_EXPANSION: bool = _bool_env(
    "MINIMAX_HAILUO_ENABLE_PROMPT_EXPANSION", False
)
MINIMAX_HAILUO_EXPANSION_FIELD: str = _str_env(
    "MINIMAX_HAILUO_EXPANSION_FIELD", "enable_prompt_expansion"
)
CHARACTER_DESCRIPTION: str = _str_env("CHARACTER_DESCRIPTION", "")
# Seedream accepts fixed sizes only (see SEEDSTREAM.md): 1024*1024, 2048*2048, 4096*2048, etc.
SEEDREAM_SIZE: str = _str_env("SEEDREAM_SIZE", "2048*2048")
SEEDREAM_ALLOWED_SIZES: tuple[str, ...] = (
    "1024*1024",
    "2048*2048",
    "4096*2048",
    "2048*4096",
)
SEEDREAM_ENABLE_SAFETY_CHECKER: bool = _bool_env("SEEDREAM_ENABLE_SAFETY_CHECKER", True)
KLING_GUIDANCE_SCALE: float = _float_env("KLING_GUIDANCE_SCALE", 0.5)
KLING_ENABLE_SAFETY_CHECKER: bool = _bool_env("KLING_ENABLE_SAFETY_CHECKER", True)
IMAGE_URL_FIELD: str = _str_env("IMAGE_URL_FIELD", "result")
IMAGE_BASE64_FIELD: str = _str_env("IMAGE_BASE64_FIELD", "image_base64")
SERVERLESS_BASE_URL: str = _str_env(
    "SERVERLESS_BASE_URL", "https://api.runpod.ai/v2"
).rstrip("/")

# API paths and transport
API_TYPE: str = _str_env("API_TYPE", "rest")
API_GENERATE_PATH: str = _str_env("API_GENERATE_PATH", "/run")
API_STATUS_PATH: str = _str_env("API_STATUS_PATH", "/status")

AUTH_HEADER_NAME: str = _str_env("AUTH_HEADER_NAME", "Authorization")
AUTH_HEADER_PREFIX: str = _str_env("AUTH_HEADER_PREFIX", "Bearer")
USE_AUTH_HEADER: bool = _bool_env("USE_AUTH_HEADER", True)

REQUEST_WRAPPER_KEY: str = _str_env("REQUEST_WRAPPER_KEY", "input")
POLLING_ENABLED: bool = _bool_env("POLLING_ENABLED", True)

# Response field mapping
JOB_ID_FIELD: str = _str_env("JOB_ID_FIELD", "id")
STATUS_FIELD: str = _str_env("STATUS_FIELD", "status")
OUTPUT_FIELD: str = _str_env("OUTPUT_FIELD", "output")
ERROR_FIELD: str = _str_env("ERROR_FIELD", "error")

STATUS_COMPLETED: str = _str_env("STATUS_COMPLETED", "COMPLETED")
STATUS_FAILED: str = _str_env("STATUS_FAILED", "FAILED")
STATUS_IN_QUEUE: str = _str_env("STATUS_IN_QUEUE", "IN_QUEUE")
STATUS_IN_PROGRESS: str = _str_env("STATUS_IN_PROGRESS", "IN_PROGRESS")

_DEFAULT_VIDEO_URL_FIELD = (
    "result"
    if PROVIDER == "runpod" and RUNPOD_PAYLOAD_PROFILE == "minimax_hailuo"
    else "video_url"
)
VIDEO_URL_FIELD: str = _str_env("VIDEO_URL_FIELD", _DEFAULT_VIDEO_URL_FIELD)
VIDEO_BASE64_FIELD: str = _str_env("VIDEO_BASE64_FIELD", "video_base64")
VIDEO_S3_FIELD: str = _str_env("VIDEO_S3_FIELD", "video_s3_uri")

# Model metadata (optional payload fields)
MODEL_FAMILY: str = _str_env(
    "MODEL_FAMILY", _str_env("MODEL_BACKEND", "wan")
)
MODEL_BACKEND: str = MODEL_FAMILY
MODEL_NAME: str = _str_env("MODEL_NAME", "wan2.2")
MODEL_TASK: str = _str_env("MODEL_TASK", _str_env("MODEL_VARIANT", "t2v"))
MODEL_VERSION: str = _str_env("MODEL_VERSION", "v43")
MODEL_INCLUDE_IN_PAYLOAD: bool = _bool_env("MODEL_INCLUDE_IN_PAYLOAD", False)
MODEL_FAMILY_FIELD: str = _str_env("MODEL_FAMILY_FIELD", "model_family")
MODEL_NAME_FIELD: str = _str_env("MODEL_NAME_FIELD", "model_name")
MODEL_TASK_FIELD: str = _str_env(
    "MODEL_TASK_FIELD", _str_env("MODEL_VARIANT_FIELD", "model_task")
)
MODEL_VERSION_FIELD: str = _str_env("MODEL_VERSION_FIELD", "model_version")

# Request payload field mapping
PROMPT_FIELD: str = _str_env("PROMPT_FIELD", "prompt")
NEGATIVE_PROMPT_FIELD: str = _str_env("NEGATIVE_PROMPT_FIELD", "negative_prompt")
WIDTH_FIELD: str = _str_env("WIDTH_FIELD", "width")
HEIGHT_FIELD: str = _str_env("HEIGHT_FIELD", "height")
FPS_FIELD: str = _str_env("FPS_FIELD", "fps")
DURATION_FIELD: str = _str_env("DURATION_FIELD", "duration_seconds")
STEPS_FIELD: str = _str_env("STEPS_FIELD", "steps")
CFG_FIELD: str = _str_env("CFG_FIELD", "cfg")
SEED_FIELD: str = _str_env("SEED_FIELD", "seed")

# Video defaults (legacy DEFAULT_* names still supported)
WIDTH: int = _int_env("WIDTH", _int_env("DEFAULT_WIDTH", 832))
HEIGHT: int = _int_env("HEIGHT", _int_env("DEFAULT_HEIGHT", 480))
FPS: int = _int_env("FPS", _int_env("DEFAULT_FPS", 16))
DURATION: int = _int_env("DURATION", _int_env("DEFAULT_DURATION_SECONDS", 5))
STEPS: int = _int_env("STEPS", _int_env("DEFAULT_STEPS", 25))
CFG: int = _int_env("CFG", _int_env("DEFAULT_CFG", 5))
SEED: int = _int_env("SEED", _int_env("DEFAULT_SEED", -1))

# Polling
POLL_INTERVAL: float = _float_env("POLL_INTERVAL", 5.0)
TIMEOUT: float = _float_env("TIMEOUT", 600.0)

# Local project paths
OUTPUT_DIR: Path = Path(os.getenv("OUTPUT_DIR", "outputs"))
if not OUTPUT_DIR.is_absolute():
    OUTPUT_DIR = _BASE_DIR / OUTPUT_DIR

CLIP_INDEX: Path = Path(os.getenv("CLIP_INDEX", "data/clips_index.json"))
if not CLIP_INDEX.is_absolute():
    CLIP_INDEX = _BASE_DIR / CLIP_INDEX

CLIP_SPECS_PATH: Path = _BASE_DIR / "data" / "clip_specs.json"
LOGS_DIR: Path = _BASE_DIR / "logs"


def validate_runtime_config() -> None:
    if PROVIDER == "aws":
        from providers.aws import validate_config

        validate_config()
        return

    if PROVIDER == "runpod":
        from providers.runpod import validate_config

        validate_config()
        return

    if PROVIDER == "minimax":
        from providers.minimax import validate_config

        validate_config()
        return

    raise RuntimeError(
        f"Unsupported PROVIDER '{PROVIDER}'. Supported providers: aws, runpod, minimax"
    )


def build_generation_payload(
    prompt: str,
    negative_prompt: str,
    seed: int | None = None,
    duration_seconds: int | None = None,
) -> dict[str, object]:
    resolved_seed = SEED if seed is None else seed
    resolved_duration = DURATION if duration_seconds is None else duration_seconds

    if PROVIDER == "runpod" and RUNPOD_PAYLOAD_PROFILE == "minimax_hailuo":
        return build_minimax_t2v_payload(
            prompt=prompt,
            duration_seconds=duration_seconds,
        )

    payload: dict[str, object] = {
        PROMPT_FIELD: prompt,
        NEGATIVE_PROMPT_FIELD: negative_prompt,
        WIDTH_FIELD: WIDTH,
        HEIGHT_FIELD: HEIGHT,
        FPS_FIELD: FPS,
        DURATION_FIELD: resolved_duration,
        STEPS_FIELD: STEPS,
        CFG_FIELD: CFG,
        SEED_FIELD: resolved_seed,
    }

    if MODEL_INCLUDE_IN_PAYLOAD:
        payload[MODEL_FAMILY_FIELD] = MODEL_FAMILY
        payload[MODEL_NAME_FIELD] = MODEL_NAME
        payload[MODEL_TASK_FIELD] = MODEL_TASK
        payload[MODEL_VERSION_FIELD] = MODEL_VERSION

    return payload


def wrap_request_body(payload: dict[str, object]) -> dict[str, object]:
    if REQUEST_WRAPPER_KEY:
        return {REQUEST_WRAPPER_KEY: payload}
    return payload


def normalize_seedream_size(raw: str | None = None) -> str:
    """Normalize Seedream size to WIDTH*HEIGHT (API also accepts WIDTHxHEIGHT)."""
    value = (raw or SEEDREAM_SIZE).strip().replace("x", "*").replace("X", "*")
    if not re.fullmatch(r"\d+\*\d+", value):
        raise ValueError(
            f"Invalid SEEDREAM_SIZE '{raw}'. Use format like '2048*2048' or '4096*2048'."
        )
    if value not in SEEDREAM_ALLOWED_SIZES:
        allowed = ", ".join(SEEDREAM_ALLOWED_SIZES)
        raise ValueError(
            f"SEEDREAM_SIZE '{value}' is not supported. Use one of: {allowed}"
        )
    return value


def build_seedream_t2i_payload(
    prompt: str,
    negative_prompt: str,
    *,
    seed: int | None = None,
    size: str | None = None,
) -> dict[str, object]:
    return {
        PROMPT_FIELD: prompt,
        NEGATIVE_PROMPT_FIELD: negative_prompt,
        "size": normalize_seedream_size(size),
        SEED_FIELD: SEED if seed is None else seed,
        "enable_safety_checker": SEEDREAM_ENABLE_SAFETY_CHECKER,
    }


def build_kling_i2v_payload(
    prompt: str,
    image_url: str,
    negative_prompt: str = "",
    *,
    duration_seconds: int | None = None,
    guidance_scale: float | None = None,
) -> dict[str, object]:
    resolved_duration = DURATION if duration_seconds is None else duration_seconds
    kling_duration = 5 if resolved_duration <= 5 else 10
    return {
        PROMPT_FIELD: prompt,
        "image": image_url,
        NEGATIVE_PROMPT_FIELD: negative_prompt,
        "guidance_scale": KLING_GUIDANCE_SCALE
        if guidance_scale is None
        else guidance_scale,
        "duration": kling_duration,
        "enable_safety_checker": KLING_ENABLE_SAFETY_CHECKER,
    }


def build_minimax_t2v_payload(
    prompt: str,
    *,
    duration_seconds: int | None = None,
) -> dict[str, object]:
    resolved_duration = DURATION if duration_seconds is None else duration_seconds
    hailuo_duration = 6 if resolved_duration <= 6 else 10
    return {
        PROMPT_FIELD: prompt,
        "duration": hailuo_duration,
        MINIMAX_HAILUO_EXPANSION_FIELD: MINIMAX_HAILUO_ENABLE_PROMPT_EXPANSION,
    }
