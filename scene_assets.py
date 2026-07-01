"""Registry of generated master images (local path + RunPod URL for I2V)."""

import json
from datetime import datetime, timezone
from pathlib import Path

from pydantic import BaseModel, Field

import config

SCENE_ASSETS_PATH = config.CLIP_SPECS_PATH.parent / "scene_assets.json"


class SceneAsset(BaseModel):
    scene_id: str
    master_filename: str
    master_path: str = ""
    master_image_url: str = ""
    updated_at: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )


def load_scene_assets(path: Path | None = None) -> dict[str, SceneAsset]:
    assets_path = path or SCENE_ASSETS_PATH
    if not assets_path.exists():
        return {}
    raw = json.loads(assets_path.read_text(encoding="utf-8"))
    return {item["scene_id"]: SceneAsset.model_validate(item) for item in raw}


def save_scene_assets(
    assets: dict[str, SceneAsset], path: Path | None = None
) -> None:
    assets_path = path or SCENE_ASSETS_PATH
    assets_path.parent.mkdir(parents=True, exist_ok=True)
    payload = [asset.model_dump(mode="json") for asset in assets.values()]
    assets_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def get_scene_asset(scene_id: str, path: Path | None = None) -> SceneAsset | None:
    return load_scene_assets(path).get(scene_id)


def upsert_scene_asset(asset: SceneAsset, path: Path | None = None) -> SceneAsset:
    assets = load_scene_assets(path)
    asset.updated_at = datetime.now(timezone.utc).isoformat()
    assets[asset.scene_id] = asset
    save_scene_assets(assets, path)
    return asset
