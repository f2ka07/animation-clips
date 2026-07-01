import os
from pathlib import Path


def _str(name: str, default: str = "") -> str:
    value = os.getenv(name)
    if value is None or value.strip() == "":
        return default
    return value.strip()


def _int(name: str, default: int) -> int:
    raw = os.getenv(name)
    if raw is None or raw.strip() == "":
        return default
    return int(raw)


def _bool(name: str, default: bool) -> bool:
    raw = os.getenv(name)
    if raw is None or raw.strip() == "":
        return default
    return raw.strip().lower() in {"1", "true", "yes", "on"}


WAN_ROOT: Path = Path(_str("WAN_ROOT", "/opt/wan"))
WAN_TASK: str = _str("WAN_TASK", "t2v-A14B")
WAN_CKPT_DIR: Path = Path(_str("WAN_CKPT_DIR", "/models/Wan2.2-T2V-A14B"))
WAN_OFFLOAD_MODEL: bool = _bool("WAN_OFFLOAD_MODEL", True)
WAN_CONVERT_MODEL_DTYPE: bool = _bool("WAN_CONVERT_MODEL_DTYPE", True)
WAN_T5_CPU: bool = _bool("WAN_T5_CPU", False)
WAN_DEFAULT_SIZE: str = _str("WAN_DEFAULT_SIZE", "832*480")

OUTPUT_DIR: Path = Path(_str("OUTPUT_DIR", "/data/videos"))
OUTPUT_MODE: str = _str("OUTPUT_MODE", "url").lower()

SERVER_HOST: str = _str("SERVER_HOST", "0.0.0.0")
SERVER_PORT: int = _int("SERVER_PORT", 8000)
PUBLIC_BASE_URL: str = _str("PUBLIC_BASE_URL", "").rstrip("/")

API_AUTH_TOKEN: str = _str("API_AUTH_TOKEN", "")
MAX_CONCURRENT_JOBS: int = _int("MAX_CONCURRENT_JOBS", 1)

STATUS_IN_QUEUE: str = _str("STATUS_IN_QUEUE", "IN_QUEUE")
STATUS_IN_PROGRESS: str = _str("STATUS_IN_PROGRESS", "IN_PROGRESS")
STATUS_COMPLETED: str = _str("STATUS_COMPLETED", "COMPLETED")
AWS_REGION: str = _str("AWS_REGION", "us-east-1")
AWS_S3_BUCKET: str = _str("AWS_S3_BUCKET", "")
AWS_S3_PREFIX: str = _str("AWS_S3_PREFIX", "videos")

ALLOWED_SIZES: dict[tuple[int, int], str] = {
    (832, 480): "832*480",
    (480, 832): "480*832",
    (1280, 720): "1280*720",
    (720, 1280): "720*1280",
    (1280, 704): "1280*704",
    (704, 1280): "704*1280",
    (1024, 704): "1024*704",
    (704, 1024): "704*1024",
}
