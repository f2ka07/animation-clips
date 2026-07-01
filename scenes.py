"""Reusable master-scene catalog for I2V clip generation."""

from enum import Enum
from pathlib import Path

from pydantic import BaseModel, Field

import config
from prompts import DEFAULT_CHARACTER_DESCRIPTION, NEGATIVE_PROMPT, normalize_duration

SCENES_PATH = config.CLIP_SPECS_PATH.parent / "scenes.json"
MASTERS_DIR = config.CLIP_SPECS_PATH.parent.parent / "masters"

MASTER_IMAGE_STYLE = (
    "Static master scene reference illustration, not animation, no motion lines, no blur. "
    "Minimalist black ink stick figure scene on off-white paper texture, educational "
    "documentary illustration, consistent line weight, no color, no text, no subtitles, "
    "no watermark, no logos, wide shot, fixed camera, single location, all props clearly visible."
)

SECONDARY_CHARACTER_DESCRIPTION = (
    "Second stick figure uses the same channel design: simple round head, two dot eyes, "
    "one short curved mouth line, straight stick limbs, three-finger hands, identical "
    "line weight and proportions to the protagonist, no hair, no clothes detail, only "
    "posture and screen position differ."
)

SUPPORTING_FIGURE_DESCRIPTION = (
    "Additional faint background stick figures use the same design system but lighter "
    "ink weight and simpler poses, never detailed faces, never more than two foreground figures."
)


class SceneFamily(str, Enum):
    OFFICE = "office"
    HOME = "home"
    PUBLIC = "public"
    EDUCATION = "education"
    HEALTH = "health"
    FITNESS = "fitness"
    TRANSIT = "transit"
    RETAIL = "retail"


class SceneRecord(BaseModel):
    id: str
    family: SceneFamily
    title: str
    variant: str
    actor_count: int = Field(ge=1, le=2)
    supporting_figures: int = Field(default=0, ge=0, le=2)
    master_filename: str
    layout: str
    composition: str
    props: list[str]
    reuse_tags: list[str]
    example_actions: list[str]
    protagonist_position: str = "center"
    secondary_position: str = ""


def load_scenes(path: Path | None = None) -> list[SceneRecord]:
    import json

    scenes_path = path or SCENES_PATH
    raw = json.loads(scenes_path.read_text(encoding="utf-8"))
    return [SceneRecord.model_validate(item) for item in raw]


def find_scene(scene_id: str, path: Path | None = None) -> SceneRecord | None:
    needle = scene_id.strip().lower()
    for scene in load_scenes(path):
        if scene.id.lower() == needle:
            return scene
    return None


def master_image_path(scene: SceneRecord) -> Path:
    return MASTERS_DIR / scene.master_filename


def build_master_image_prompt(
    scene: SceneRecord,
    *,
    character_description: str | None = None,
) -> str:
    character = (character_description or DEFAULT_CHARACTER_DESCRIPTION).strip()
    parts = [
        MASTER_IMAGE_STYLE,
        f"Scene id: {scene.id}.",
        f"Character: {character}",
    ]

    if scene.actor_count >= 2:
        parts.append(f"Secondary figure: {SECONDARY_CHARACTER_DESCRIPTION}")
        if scene.secondary_position:
            parts.append(f"Positioning: protagonist {scene.protagonist_position}, "
                         f"secondary figure {scene.secondary_position}.")
    elif scene.protagonist_position:
        parts.append(f"Positioning: protagonist {scene.protagonist_position}.")

    if scene.supporting_figures:
        parts.append(SUPPORTING_FIGURE_DESCRIPTION)
        parts.append(
            f"Include up to {scene.supporting_figures} faint background stick figures."
        )

    parts.append(f"Layout: {scene.layout}")
    parts.append(f"Composition: {scene.composition}")
    parts.append(f"Props (all visible, stationary): {', '.join(scene.props)}.")
    parts.append(
        "Output a single still frame suitable as a reusable master image for later animation."
    )
    return " ".join(parts)


def build_i2v_animation_prompt(
    scene: SceneRecord,
    action: str,
    *,
    duration_seconds: int | None = None,
    character_description: str | None = None,
) -> str:
    duration = normalize_duration(duration_seconds)
    character = (character_description or DEFAULT_CHARACTER_DESCRIPTION).strip()
    action_text = action.strip()

    actor_line = (
        "Animate only the two foreground stick figures."
        if scene.actor_count >= 2
        else "Animate only the protagonist stick figure."
    )

    return (
        f"Image-to-video animation from the master scene {scene.id}. "
        f"Keep the room, props, camera, and character designs visually identical to the "
        f"input image. {actor_line} Static camera, no scene change, no new props, no text, "
        f"no color, black ink style on off-white paper, {duration} second clip. "
        f"Character: {character} "
        f"Action: {action_text}"
    )


def scenes_by_family(
    family: SceneFamily | str, path: Path | None = None
) -> list[SceneRecord]:
    needle = family.value if isinstance(family, SceneFamily) else str(family).lower()
    return [scene for scene in load_scenes(path) if scene.family.value == needle]


def scenes_by_tag(tag: str, path: Path | None = None) -> list[SceneRecord]:
    needle = tag.strip().lower()
    return [
        scene
        for scene in load_scenes(path)
        if any(item.lower() == needle for item in scene.reuse_tags)
    ]
