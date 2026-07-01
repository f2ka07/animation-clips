"""Generate a master scene still image via RunPod Seedream T2I (prompt from scenes.json)."""

import argparse
import json
import sys
from datetime import datetime, timezone

from pydantic import BaseModel
from rich.console import Console
from rich.table import Table

import config
from prompts import NEGATIVE_PROMPT
from providers.runpod_serverless import extract_media_url, run_job, save_media
from scene_assets import SceneAsset, upsert_scene_asset
from scenes import SceneRecord, build_master_image_prompt, find_scene, load_scenes, master_image_path

console = Console()

MAX_RETRIES = 2
SEEDREAM_COST_PER_REQUEST = 0.027


class MasterBatchFailure(BaseModel):
    scene_id: str
    attempts: int
    error: str


def missing_scenes(*, force: bool = False) -> list[SceneRecord]:
    scenes = load_scenes()
    if force:
        return scenes
    return [scene for scene in scenes if not master_image_path(scene).exists()]


def estimate_phase1_cost(count: int) -> float:
    return round(count * SEEDREAM_COST_PER_REQUEST, 4)


def generate_master_for_scene(
    scene_id: str, *, dry_run: bool = False, force: bool = False
) -> bool:
    scene = find_scene(scene_id)
    if scene is None:
        raise ValueError(f"Scene not found in scenes.json: {scene_id}")

    destination = master_image_path(scene)
    if destination.exists() and not force:
        console.print(f"[yellow]Skipping[/yellow] {scene.id} (master exists: {destination})")
        return False

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
        return True

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
    return True


def run_phase1_batch(
    *,
    dry_run: bool = False,
    force: bool = False,
    limit: int | None = None,
) -> list[MasterBatchFailure]:
    pending = missing_scenes(force=force)
    if limit is not None:
        pending = pending[:limit]

    total = len(pending)
    if total == 0:
        console.print("[green]Phase 1 complete. All master images exist.[/green]")
        return []

    cost = estimate_phase1_cost(total)
    console.print(f"[bold]Phase 1[/bold] Generate {total} master image(s)")
    console.print(f"Estimated cost: ${cost:.2f} ({SEEDREAM_COST_PER_REQUEST:.4f} each)")
    console.print(f"Endpoint: {config.RUNPOD_T2I_ENDPOINT_ID}")
    console.print(f"Size: {config.normalize_seedream_size()}")
    console.print()

    failures: list[MasterBatchFailure] = []
    generated = 0
    skipped = 0

    for index, scene in enumerate(pending, start=1):
        console.print(f"[bold cyan][{index}/{total}][/bold cyan] {scene.id}")
        last_error = "Unknown error"
        succeeded = False

        for attempt in range(1, MAX_RETRIES + 2):
            try:
                created = generate_master_for_scene(
                    scene.id, dry_run=dry_run, force=force
                )
                if created:
                    generated += 1
                else:
                    skipped += 1
                succeeded = True
                break
            except Exception as exc:
                last_error = str(exc)
                console.print(
                    f"[yellow]Attempt {attempt} failed for {scene.id}:[/yellow] {exc}"
                )
                if attempt > MAX_RETRIES:
                    failures.append(
                        MasterBatchFailure(
                            scene_id=scene.id,
                            attempts=attempt,
                            error=last_error,
                        )
                    )

        if not succeeded and not dry_run:
            continue

    table = Table(show_header=True, header_style="bold")
    table.add_column("Metric")
    table.add_column("Count")
    table.add_row("Requested", str(total))
    table.add_row("Generated", str(generated))
    table.add_row("Skipped", str(skipped))
    table.add_row("Failed", str(len(failures)))
    if not dry_run:
        table.add_row("Est. spent", f"${estimate_phase1_cost(generated):.2f}")
    console.print()
    console.print(table)

    if failures:
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        failure_path = config.LOGS_DIR / f"batch_master_failures_{timestamp}.json"
        failure_path.parent.mkdir(parents=True, exist_ok=True)
        failure_path.write_text(
            json.dumps([item.model_dump() for item in failures], indent=2),
            encoding="utf-8",
        )
        console.print(f"[red]Failures saved to:[/red] {failure_path}")

    return failures


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
        "--phase1",
        action="store_true",
        help="Run full phase 1 batch (all missing masters, with summary)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print prompt and print payload without calling the API",
    )
    parser.add_argument("--force", action="store_true", help="Overwrite existing master PNG")
    parser.add_argument("--limit", type=int, help="Max scenes to process in batch mode")
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    if args.phase1 or args.all_missing:
        failures = run_phase1_batch(
            dry_run=args.dry_run,
            force=args.force,
            limit=args.limit,
        )
        if failures:
            sys.exit(1)
        return

    if not args.scene:
        console.print("Provide --scene <id>, --phase1, or --all-missing")
        sys.exit(1)

    try:
        generate_master_for_scene(args.scene, dry_run=args.dry_run, force=args.force)
    except Exception as exc:
        console.print(f"[red]Failed {args.scene}:[/red] {exc}")
        sys.exit(1)


if __name__ == "__main__":
    main()
