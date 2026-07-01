from pathlib import Path

from dotenv import load_dotenv
import os

load_dotenv()

_BASE_DIR = Path(__file__).resolve().parent


def _require(name: str) -> str:
    value = os.getenv(name)
    if not value:
        raise RuntimeError(
            f"Missing required environment variable: {name}. "
            f"Copy .env.example to .env and set {name}."
        )
    return value


def _int_env(name: str, default: int) -> int:
    raw = os.getenv(name)
    if raw is None or raw.strip() == "":
        return default
    return int(raw)


def get_runpod_api_key() -> str:
    return _require("RUNPOD_API_KEY")


def get_runpod_endpoint_id() -> str:
    return _require("RUNPOD_ENDPOINT_ID")
OUTPUT_DIR: Path = Path(os.getenv("OUTPUT_DIR", "outputs"))
if not OUTPUT_DIR.is_absolute():
    OUTPUT_DIR = _BASE_DIR / OUTPUT_DIR

CLIP_INDEX: Path = Path(os.getenv("CLIP_INDEX", "data/clips_index.json"))
if not CLIP_INDEX.is_absolute():
    CLIP_INDEX = _BASE_DIR / CLIP_INDEX

DEFAULT_DURATION_SECONDS: int = _int_env("DEFAULT_DURATION_SECONDS", 5)
DEFAULT_FPS: int = _int_env("DEFAULT_FPS", 16)
DEFAULT_WIDTH: int = _int_env("DEFAULT_WIDTH", 832)
DEFAULT_HEIGHT: int = _int_env("DEFAULT_HEIGHT", 480)
DEFAULT_STEPS: int = _int_env("DEFAULT_STEPS", 25)
DEFAULT_CFG: int = _int_env("DEFAULT_CFG", 5)
DEFAULT_SEED: int = _int_env("DEFAULT_SEED", -1)

POLL_INTERVAL_SECONDS: float = 5.0
JOB_TIMEOUT_SECONDS: float = 600.0

CLIP_SPECS_PATH: Path = _BASE_DIR / "data" / "clip_specs.json"
LOGS_DIR: Path = _BASE_DIR / "logs"
