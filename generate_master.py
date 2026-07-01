"""Generate a master scene still image via RunPod Seedream T2I (prompt from scenes.json)."""

import argparse
import sys

from rich.console import Console

import config
from prompts import NEGATIVE_PROMPT
from providers.runpod_serverless import extract_media_url, run_job, save_media
from scene_assets import SceneAsset, upsert_scene_asset
from scenes import build_master_image_prompt, find_scene, load_scenes, master_image_path

console = Console()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate master scene PNGs using RunPod T2I (seedream-v4-t2i)."
    )
    parser.add_argument("--scene", help="Scene id from data/scenes.json")
    parser.add_argument(
        "--all-missing",
        action="store_true",
        help="Generate masters for scenes without a local PNG",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print prompt and payload without calling the API",
    )
    parser.add_argument("--force", action="store_true", help="Overwrite existing master PNG")
    return parser.parse_args()


def generate_master_for_scene(scene_id: str, *, dry_run: bool = False, force: bool = False) -> None:
    scene = find_scene(scene_id)
    if scene is None:
        raise ValueError(f"Scene not found in scenes.json: {scene_id}")

    destination = master_image_path(scene)
    if destination.exists() and not force:
        console.print(f"[yellow]Skipping[/yellow] {scene.id} (master exists: {destination})")
        return

    prompt = build_master_image_prompt(
        scene,
        character_description=config.CHARACTER_DESCRIPTION or None,
    )
    payload = config.build_seedream_t2i_payload(prompt, NEGATIVE_PROMPT)

    if dry_run:
        console.print(f"[bold]Scene[/bold] {scene.id}")
        console.print(f"[bold]Endpoint[/bold] {config.RUNPOD_T2I_ENDPOINT_ID}")
        console.print("[bold]Prompt[/bold]")
        console.print(prompt)
        console.print("[bold]Payload[/bold]")
        console.print(payload)
        return

    output = run_job(config.RUNPOD_T2I_ENDPOINT_ID, payload)
    image_url = extract_media_url(output)
    save_media(output, destination)

    upsert_scene_asset(
        SceneAsset(
            scene_id=scene.id,
            master_filename=scene.master_filename,
            master_path=str(destination),
            master_image_url=image_url,
        )
    )
    console.print(f"[green]Saved master[/green] {destination}")
    console.print(f"[green]Image URL[/green] {image_url}")


def main() -> None:
    args = parse_args()

    if not args.scene and not args.all_missing:
        console.print("Provide --scene <id> or --all-missing")
        sys.exit(1)

    scene_ids = [args.scene] if args.scene else []
    if args.all_missing:
        scene_ids = [
            scene.id
            for scene in load_scenes()
            if not master_image_path(scene).exists()
        ]
        console.print(f"Missing masters: {len(scene_ids)}")

    errors = 0
    for scene_id in scene_ids:
        if not scene_id:
            continue
        try:
            generate_master_for_scene(scene_id, dry_run=args.dry_run, force=args.force)
        except Exception as exc:
            errors += 1
            console.print(f"[red]Failed {scene_id}:[/red] {exc}")

    if errors:
        sys.exit(1)


if __name__ == "__main__":
    main()
