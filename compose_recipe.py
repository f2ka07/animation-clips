import argparse
import json
from pathlib import Path

from pydantic import BaseModel
from rich.console import Console
from rich.table import Table

import config
from library import ClipRecord, find_by_title, load_index

console = Console()


class RecipeClipRef(BaseModel):
    title: str
    category: str


class VideoRecipe(BaseModel):
    id: str
    title: str
    description: str
    target_duration_seconds: int
    clips: list[RecipeClipRef]


def load_recipes(path: Path | None = None) -> list[VideoRecipe]:
    recipes_path = path or config.CLIP_SPECS_PATH.parent / "video_recipes.json"
    raw = json.loads(recipes_path.read_text(encoding="utf-8"))
    return [VideoRecipe.model_validate(item) for item in raw]


def resolve_clip(ref: RecipeClipRef, approved_only: bool = True) -> tuple[ClipRecord | None, str]:
    matches = find_by_title(ref.title)
    for clip in matches:
        if clip.category.lower() != ref.category.lower():
            continue
        if clip.status.value != "completed":
            continue
        if approved_only and clip.review_status.value != "approved":
            return None, clip.review_status.value
        return clip, "approved"
    return None, "missing"


def show_recipe(recipe: VideoRecipe) -> None:
    console.print(f"[bold]{recipe.title}[/bold]")
    console.print(recipe.description)
    console.print(f"Target length: ~{recipe.target_duration_seconds}s")
    console.print()

    table = Table(show_header=True, header_style="bold")
    table.add_column("#")
    table.add_column("Title")
    table.add_column("Category")
    table.add_column("Status")
    table.add_column("File")

    total_duration = 0
    for index, ref in enumerate(recipe.clips, start=1):
        clip, state = resolve_clip(ref)
        if clip:
            total_duration += clip.duration_seconds
            table.add_row(
                str(index),
                ref.title,
                ref.category,
                clip.status.value,
                clip.filename or "-",
            )
        else:
            status = "[red]missing[/red]" if state == "missing" else f"[yellow]{state}[/yellow]"
            table.add_row(
                str(index),
                ref.title,
                ref.category,
                status,
                "-",
            )

    console.print(table)
    console.print(f"Resolved clip duration total: ~{total_duration}s")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="List stitchable clip recipes and resolved library files."
    )
    parser.add_argument("--list", action="store_true", help="List all recipes")
    parser.add_argument("--recipe", help="Recipe id to inspect")
    parser.add_argument(
        "--recipes",
        type=Path,
        default=config.CLIP_SPECS_PATH.parent / "video_recipes.json",
    )
    args = parser.parse_args()
    recipes = load_recipes(args.recipes)

    if args.list:
        for recipe in recipes:
            console.print(f"- {recipe.id}: {recipe.title} ({len(recipe.clips)} clips)")
        return

    if not args.recipe:
        parser.error("Use --list or --recipe <id>")

    match = next((recipe for recipe in recipes if recipe.id == args.recipe), None)
    if match is None:
        console.print(f"[red]Recipe not found:[/red] {args.recipe}")
        raise SystemExit(1)

    show_recipe(match)


if __name__ == "__main__":
    main()
