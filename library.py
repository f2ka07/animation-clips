import argparse
import json
import re
import uuid
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path

from pydantic import BaseModel, Field
from rich.console import Console
from rich.table import Table

import config

console = Console()


class ClipStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class ClipRecord(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    title: str
    category: str
    tags: list[str]
    prompt: str
    negative_prompt: str
    filename: str = ""
    duration_seconds: int
    width: int
    height: int
    fps: int
    steps: int
    cfg: int
    seed: int
    created_at: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    status: ClipStatus = ClipStatus.PENDING


def load_index(path: Path | None = None) -> list[ClipRecord]:
    index_path = path or config.CLIP_INDEX
    if not index_path.exists():
        return []
    raw = json.loads(index_path.read_text(encoding="utf-8"))
    return [ClipRecord.model_validate(item) for item in raw]


def save_index(clips: list[ClipRecord], path: Path | None = None) -> None:
    index_path = path or config.CLIP_INDEX
    index_path.parent.mkdir(parents=True, exist_ok=True)
    payload = [clip.model_dump(mode="json") for clip in clips]
    index_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def add_clip(record: ClipRecord, path: Path | None = None) -> ClipRecord:
    clips = load_index(path)
    clips.append(record)
    save_index(clips, path)
    return record


def update_clip(record: ClipRecord, path: Path | None = None) -> None:
    clips = load_index(path)
    for i, clip in enumerate(clips):
        if clip.id == record.id:
            clips[i] = record
            save_index(clips, path)
            return
    clips.append(record)
    save_index(clips, path)


def find_by_tag(tag: str, path: Path | None = None) -> list[ClipRecord]:
    needle = tag.strip().lower()
    return [
        clip
        for clip in load_index(path)
        if any(t.lower() == needle for t in clip.tags)
    ]


def find_by_category(category: str, path: Path | None = None) -> list[ClipRecord]:
    needle = category.strip().lower()
    return [clip for clip in load_index(path) if clip.category.lower() == needle]


def find_by_title(title: str, path: Path | None = None) -> list[ClipRecord]:
    needle = title.strip().lower()
    return [clip for clip in load_index(path) if clip.title.lower() == needle]


def find_completed_by_title_category(
    title: str, category: str, path: Path | None = None
) -> ClipRecord | None:
    for clip in load_index(path):
        if (
            clip.title.lower() == title.strip().lower()
            and clip.category.lower() == category.strip().lower()
            and clip.status == ClipStatus.COMPLETED
        ):
            return clip
    return None


def find_failed_by_title_category(
    title: str, category: str, path: Path | None = None
) -> ClipRecord | None:
    for clip in load_index(path):
        if (
            clip.title.lower() == title.strip().lower()
            and clip.category.lower() == category.strip().lower()
            and clip.status == ClipStatus.FAILED
        ):
            return clip
    return None


def sanitize_filename_part(value: str) -> str:
    cleaned = re.sub(r"[^\w\s-]", "", value.strip().lower())
    cleaned = re.sub(r"[\s_-]+", "_", cleaned)
    return cleaned.strip("_") or "clip"


def build_output_filename(category: str, title: str) -> str:
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    category_part = sanitize_filename_part(category)
    title_part = sanitize_filename_part(title)
    return f"{category_part}_{title_part}_{timestamp}.mp4"


def _print_clips(clips: list[ClipRecord]) -> None:
    if not clips:
        console.print("[yellow]No clips found.[/yellow]")
        return

    table = Table(show_header=True, header_style="bold")
    table.add_column("Title")
    table.add_column("Category")
    table.add_column("Status")
    table.add_column("Tags")
    table.add_column("Filename")

    for clip in clips:
        table.add_row(
            clip.title,
            clip.category,
            clip.status.value,
            ", ".join(clip.tags),
            clip.filename or "-",
        )

    console.print(table)


def main() -> None:
    parser = argparse.ArgumentParser(description="Search the clip library.")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--tag", help="Find clips by tag")
    group.add_argument("--category", help="Find clips by category")
    group.add_argument("--title", help="Find clips by title")
    args = parser.parse_args()

    if args.tag:
        clips = find_by_tag(args.tag)
    elif args.category:
        clips = find_by_category(args.category)
    else:
        clips = find_by_title(args.title)

    _print_clips(clips)


if __name__ == "__main__":
    main()
