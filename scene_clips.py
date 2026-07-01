"""Track I2V clips generated from master scenes."""

import json
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path

from pydantic import BaseModel, Field

import config

SCENE_CLIPS_INDEX_PATH = config.CLIP_SPECS_PATH.parent / "scene_clips_index.json"


class SceneClipStatus(str, Enum):
    COMPLETED = "completed"
    FAILED = "failed"


class SceneClipRecord(BaseModel):
    scene_id: str
    action_index: int
    title: str
    category: str
    action: str
    prompt: str
    filename: str = ""
    master_image_url: str = ""
    duration_seconds: int = 5
    status: SceneClipStatus = SceneClipStatus.COMPLETED
    updated_at: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )


def clip_title(scene_id: str, action_index: int) -> str:
    return f"{scene_id}_a{action_index}"


def load_scene_clips(path: Path | None = None) -> list[SceneClipRecord]:
    index_path = path or SCENE_CLIPS_INDEX_PATH
    if not index_path.exists():
        return []
    raw = json.loads(index_path.read_text(encoding="utf-8"))
    return [SceneClipRecord.model_validate(item) for item in raw]


def save_scene_clips(records: list[SceneClipRecord], path: Path | None = None) -> None:
    index_path = path or SCENE_CLIPS_INDEX_PATH
    index_path.parent.mkdir(parents=True, exist_ok=True)
    payload = [record.model_dump(mode="json") for record in records]
    index_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def find_scene_clip(
    scene_id: str, action_index: int, path: Path | None = None
) -> SceneClipRecord | None:
    for record in load_scene_clips(path):
        if (
            record.scene_id == scene_id
            and record.action_index == action_index
            and record.status == SceneClipStatus.COMPLETED
        ):
            return record
    return None


def upsert_scene_clip(record: SceneClipRecord, path: Path | None = None) -> SceneClipRecord:
    records = load_scene_clips(path)
    record.updated_at = datetime.now(timezone.utc).isoformat()
    replaced = False
    for index, existing in enumerate(records):
        if existing.scene_id == record.scene_id and existing.action_index == record.action_index:
            records[index] = record
            replaced = True
            break
    if not replaced:
        records.append(record)
    save_scene_clips(records, path)
    return record
