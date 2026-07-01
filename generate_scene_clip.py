"""Animate a master scene via RunPod Kling I2V (prompt + image from scenes.json assets)."""

import argparse
import sys
from datetime import datetime, timezone
from pathlib import Path

from rich.console import Console

import config
from prompts import NEGATIVE_PROMPT
from providers.runpod_serverless import run_job, save_media
from scene_assets import get_scene_asset
from scenes import (
    build_i2v_animation_prompt,
    find_scene,
    master_image_path,
)

console = Console()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate a clip from a master scene using RunPod Kling I2V."
    )
    parser.add_argument("--scene", required=True, help="Scene id from data/scenes.json")
    parser.add_argument(
        "--action",
        help="Animation action text (overrides --action-index)",
    )
    parser.add_argument(
        "--action-index",
        type=int,
        default=0,
        help="Pick example_actions[index] from scenes.json",
    )
    parser.add_argument("--duration", type=int, default=5, choices=[5, 6, 10])
    parser.add_argument(
        "--title",
        help="Clip title for output filename (default: scene id + timestamp)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print prompts and payload without calling the API",
    )
    return parser.parse_args()


def resolve_image_url(scene_id: str) -> str:
    asset = get_scene_asset(scene_id)
    if asset and asset.master_image_url:
        return asset.master_image_url

    raise ValueError(
        f"No master_image_url for scene '{scene_id}'. "
        f"Run: python generate_master.py --scene {scene_id}"
    )


def build_output_path(scene_id: str, title: str | None) -> Path:
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    slug = (title or scene_id).lower().replace(" ", "_")
    filename = f"{scene_id}_{slug}_{stamp}.mp4"
    return config.OUTPUT_DIR / filename


def main() -> None:
    args = parse_args()

    scene = find_scene(args.scene)
    if scene is None:
        console.print(f"[red]Scene not found:[/red] {args.scene}")
        sys.exit(1)

    master_path = master_image_path(scene)
    if not master_path.exists():
        console.print(
            f"[yellow]Warning:[/yellow] local master missing at {master_path} "
            "(I2V will still use RunPod image URL if present)"
        )

    if args.action:
        action = args.action
    elif scene.example_actions:
        if args.action_index < 0 or args.action_index >= len(scene.example_actions):
            console.print(
                f"[red]action-index must be 0..{len(scene.example_actions) - 1}[/red]"
            )
            sys.exit(1)
        action = scene.example_actions[args.action_index]
    else:
        console.print("[red]Provide --action or define example_actions in scenes.json[/red]")
        sys.exit(1)

    animation_prompt = build_i2v_animation_prompt(
        scene,
        action,
        duration_seconds=args.duration,
        character_description=config.CHARACTER_DESCRIPTION or None,
    )

    try:
        image_url = resolve_image_url(scene.id)
    except ValueError as exc:
        if args.dry_run:
            image_url = "https://image.runpod.ai/.../master.png  # run generate_master.py first"
            console.print(f"[yellow]{exc}[/yellow]")
        else:
            console.print(f"[red]{exc}[/red]")
            sys.exit(1)

    payload = config.build_kling_i2v_payload(
        animation_prompt,
        image_url,
        NEGATIVE_PROMPT,
        duration_seconds=args.duration,
    )

    if args.dry_run:
        console.print(f"[bold]Scene[/bold] {scene.id}")
        console.print(f"[bold]Endpoint[/bold] {config.RUNPOD_I2V_ENDPOINT_ID}")
        console.print(f"[bold]Image URL[/bold] {image_url}")
        console.print("[bold]Animation prompt[/bold]")
        console.print(animation_prompt)
        console.print("[bold]Payload[/bold]")
        console.print(payload)
        return

    output = run_job(config.RUNPOD_I2V_ENDPOINT_ID, payload)
    destination = build_output_path(scene.id, args.title)
    save_media(output, destination)
    console.print(f"[green]Saved clip[/green] {destination}")
    console.print(
        "[dim]Review and index with library workflow when ready.[/dim]"
    )


if __name__ == "__main__":
    main()
