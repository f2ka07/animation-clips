"""Stitch scene clips into a trial video with ffmpeg."""

import argparse
import json
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

from pydantic import BaseModel, Field
from rich.console import Console
from rich.table import Table

import config
from scene_clips import SceneClipStatus, find_scene_clip, load_scene_clips

console = Console()


class StitchClipRef(BaseModel):
    scene_id: str
    action_index: int = 0


class StitchRecipe(BaseModel):
    id: str
    title: str
    description: str = ""
    target_duration_seconds: int = 0
    clips: list[StitchClipRef]


def load_stitch_recipe(path: Path) -> StitchRecipe:
    raw = json.loads(path.read_text(encoding="utf-8"))
    return StitchRecipe.model_validate(raw)


def resolve_clip_path(scene_id: str, action_index: int) -> Path | None:
    record = find_scene_clip(scene_id, action_index)
    if record is None or record.status != SceneClipStatus.COMPLETED:
        return None
    path = config.OUTPUT_DIR / record.filename
    if path.exists():
        return path
    if record.filename:
        alt = config.OUTPUT_DIR / Path(record.filename).name
        if alt.exists():
            return alt
    return None


def stitch_recipe(
    recipe: StitchRecipe,
    output_path: Path | None = None,
    *,
    require_all: bool = True,
) -> Path:
    resolved: list[Path] = []
    missing: list[str] = []

    for ref in recipe.clips:
        path = resolve_clip_path(ref.scene_id, ref.action_index)
        label = f"{ref.scene_id}_a{ref.action_index}"
        if path is None:
            missing.append(label)
            continue
        resolved.append(path)

    if missing:
        console.print("[yellow]Missing clips:[/yellow]")
        for item in missing:
            console.print(f"  - {item}")
        if require_all:
            raise FileNotFoundError(
                f"{len(missing)} clip(s) missing. Generate with batch_scene_clips.py first."
            )

    if not resolved:
        raise FileNotFoundError("No clips resolved for stitching.")

    if output_path is None:
        stamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        output_path = config.OUTPUT_DIR / f"{recipe.id}_{stamp}.mp4"

    output_path.parent.mkdir(parents=True, exist_ok=True)

    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".txt", delete=False, encoding="utf-8"
    ) as handle:
        list_path = Path(handle.name)
        for clip_path in resolved:
            escaped = str(clip_path.resolve()).replace("'", "'\\''")
            handle.write(f"file '{escaped}'\n")

    console.print(f"[cyan]Stitching[/cyan] {len(resolved)} clips -> {output_path}")
    cmd = [
        "ffmpeg",
        "-y",
        "-f",
        "concat",
        "-safe",
        "0",
        "-i",
        str(list_path),
        "-c",
        "copy",
        str(output_path),
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    list_path.unlink(missing_ok=True)

    if result.returncode != 0:
        console.print(result.stderr)
        raise RuntimeError(f"ffmpeg failed with exit code {result.returncode}")

    return output_path


def preview_recipe(recipe: StitchRecipe) -> None:
    console.print(f"[bold]{recipe.title}[/bold]")
    console.print(recipe.description)
    console.print()

    table = Table(show_header=True, header_style="bold")
    table.add_column("#")
    table.add_column("Scene")
    table.add_column("File")
    table.add_column("Status")

    total_seconds = 0
    for index, ref in enumerate(recipe.clips, start=1):
        record = find_scene_clip(ref.scene_id, ref.action_index)
        path = resolve_clip_path(ref.scene_id, ref.action_index)
        if record and path:
            total_seconds += record.duration_seconds
            status = "ready"
            file_label = path.name
        else:
            status = "[red]missing[/red]"
            file_label = "-"
        table.add_row(str(index), ref.scene_id, file_label, status)

    console.print(table)
    console.print(f"Resolved duration: ~{total_seconds}s")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Stitch scene clips into a trial MP4.")
    parser.add_argument(
        "--recipe",
        type=Path,
        default=config.CLIP_SPECS_PATH.parent / "trial_video.json",
    )
    parser.add_argument(
        "--output",
        type=Path,
        help="Output MP4 path (default: outputs/<recipe_id>_<timestamp>.mp4)",
    )
    parser.add_argument("--preview", action="store_true", help="Show resolved clips only")
    parser.add_argument(
        "--allow-missing",
        action="store_true",
        help="Stitch available clips even if some are missing",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    recipe = load_stitch_recipe(args.recipe)

    if args.preview:
        preview_recipe(recipe)
        return

    try:
        output = stitch_recipe(
            recipe,
            args.output,
            require_all=not args.allow_missing,
        )
    except Exception as exc:
        console.print(f"[red]Stitch failed:[/red] {exc}")
        sys.exit(1)

    console.print(f"[green]Trial video saved:[/green] {output}")


if __name__ == "__main__":
    main()
