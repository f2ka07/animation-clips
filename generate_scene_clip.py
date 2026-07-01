"""Animate master scenes via RunPod Kling I2V (prompt + image from scenes.json)."""

from pathlib import Path

import argparse
import json
import sys
from datetime import datetime, timezone

from pydantic import BaseModel
from rich.console import Console
from rich.table import Table

import config
from library import ClipRecord, ClipStatus, ReviewStatus, add_clip, build_output_filename
from prompts import NEGATIVE_PROMPT
from providers.runpod_serverless import run_job, save_media
from scene_assets import get_scene_asset
from scene_clips import (
    SceneClipRecord,
    SceneClipStatus,
    clip_title,
    find_scene_clip,
    upsert_scene_clip,
)
from scenes import SceneRecord, build_i2v_animation_prompt, find_scene, load_scenes

console = Console()

MAX_RETRIES = 2
KLING_COST_5S = 0.45
KLING_COST_10S = 0.90


class SceneClipBatchFailure(BaseModel):
    scene_id: str
    action_index: int
    attempts: int
    error: str


def resolve_image_url(scene_id: str) -> str:
    asset = get_scene_asset(scene_id)
    if asset and asset.master_image_url:
        return asset.master_image_url
    raise ValueError(
        f"No master_image_url for scene '{scene_id}'. "
        f"Run: python generate_master.py --scene {scene_id}"
    )


def estimate_i2v_cost(count: int, duration_seconds: int) -> float:
    unit = KLING_COST_5S if duration_seconds <= 5 else KLING_COST_10S
    return round(count * unit, 2)


def iter_phase2_jobs(
    *,
    scene_filter: str | None = None,
    action_indices: list[int] | None = None,
    skip_existing: bool = True,
) -> list[tuple[SceneRecord, int, str]]:
    indices = action_indices if action_indices is not None else [0, 1, 2]
    jobs: list[tuple[SceneRecord, int, str]] = []

    for scene in load_scenes():
        if scene_filter and scene.id != scene_filter:
            continue
        try:
            resolve_image_url(scene.id)
        except ValueError:
            console.print(f"[yellow]Skipping {scene.id}:[/yellow] no master image URL")
            continue

        for action_index in indices:
            if action_index < 0 or action_index >= len(scene.example_actions):
                continue
            if skip_existing and find_scene_clip(scene.id, action_index):
                continue
            jobs.append((scene, action_index, scene.example_actions[action_index]))

    return jobs


def generate_scene_clip(
    scene_id: str,
    action_index: int,
    *,
    action: str | None = None,
    duration_seconds: int = 5,
    dry_run: bool = False,
    force: bool = False,
) -> "Path | None":
    scene = find_scene(scene_id)
    if scene is None:
        raise ValueError(f"Scene not found: {scene_id}")

    if not force and find_scene_clip(scene.id, action_index):
        console.print(
            f"[yellow]Skipping[/yellow] {clip_title(scene.id, action_index)} (already completed)"
        )
        return None

    if action is None:
        if action_index < 0 or action_index >= len(scene.example_actions):
            raise ValueError(f"action_index out of range for scene {scene_id}")
        action = scene.example_actions[action_index]

    animation_prompt = build_i2v_animation_prompt(
        scene,
        action,
        duration_seconds=duration_seconds,
        character_description=config.CHARACTER_DESCRIPTION or None,
    )
    image_url = resolve_image_url(scene.id)

    payload = config.build_kling_i2v_payload(
        animation_prompt,
        image_url,
        NEGATIVE_PROMPT,
        duration_seconds=duration_seconds,
    )

    title = clip_title(scene.id, action_index)
    category = scene.family.value

    if dry_run:
        console.print(f"[bold]Scene[/bold] {scene.id} action {action_index}")
        console.print(f"[bold]Title[/bold] {title}")
        console.print(f"[bold]Image URL[/bold] {image_url}")
        console.print("[bold]Animation prompt[/bold]")
        console.print(animation_prompt)
        console.print("[bold]Payload[/bold]")
        console.print(payload)
        return None

    output = run_job(config.RUNPOD_I2V_ENDPOINT_ID, payload)
    filename = build_output_filename(category, title)
    destination = config.OUTPUT_DIR / filename
    save_media(output, destination)

    upsert_scene_clip(
        SceneClipRecord(
            scene_id=scene.id,
            action_index=action_index,
            title=title,
            category=category,
            action=action,
            prompt=animation_prompt,
            filename=filename,
            master_image_url=image_url,
            duration_seconds=duration_seconds,
            status=SceneClipStatus.COMPLETED,
        )
    )

    tags = list(dict.fromkeys([scene.id, scene.family.value, *scene.reuse_tags]))
    add_clip(
        ClipRecord(
            title=title,
            category=category,
            tags=tags,
            prompt=animation_prompt,
            negative_prompt=NEGATIVE_PROMPT,
            filename=filename,
            duration_seconds=duration_seconds,
            width=config.WIDTH,
            height=config.HEIGHT,
            fps=config.FPS,
            steps=config.STEPS,
            cfg=config.CFG,
            seed=config.SEED,
            status=ClipStatus.COMPLETED,
            review_status=ReviewStatus.PENDING_REVIEW,
        )
    )

    console.print(f"[green]Saved clip[/green] {destination}")
    return destination


def run_phase2_batch(
    *,
    dry_run: bool = False,
    force: bool = False,
    limit: int | None = None,
    scene_filter: str | None = None,
    action_indices: list[int] | None = None,
    duration_seconds: int = 5,
) -> list[SceneClipBatchFailure]:
    jobs = iter_phase2_jobs(
        scene_filter=scene_filter,
        action_indices=action_indices,
        skip_existing=not force,
    )
    if limit is not None:
        jobs = jobs[:limit]

    total = len(jobs)
    if total == 0:
        console.print("[green]Phase 2 complete. No pending scene clips.[/green]")
        return []

    cost = estimate_i2v_cost(total, duration_seconds)
    console.print(f"[bold]Phase 2[/bold] Generate {total} I2V clip(s) @ {duration_seconds}s")
    console.print(f"Estimated cost: ${cost:.2f}")
    console.print(f"Endpoint: {config.RUNPOD_I2V_ENDPOINT_ID}")
    console.print()

    failures: list[SceneClipBatchFailure] = []
    generated = 0
    skipped = 0

    for index, (scene, action_index, action) in enumerate(jobs, start=1):
        label = clip_title(scene.id, action_index)
        console.print(f"[bold cyan][{index}/{total}][/bold cyan] {label}")
        last_error = "Unknown error"
        succeeded = False

        for attempt in range(1, MAX_RETRIES + 2):
            try:
                result = generate_scene_clip(
                    scene.id,
                    action_index,
                    action=action,
                    duration_seconds=duration_seconds,
                    dry_run=dry_run,
                    force=force,
                )
                if result is None and not dry_run:
                    skipped += 1
                else:
                    generated += 1
                succeeded = True
                break
            except Exception as exc:
                last_error = str(exc)
                console.print(
                    f"[yellow]Attempt {attempt} failed for {label}:[/yellow] {exc}"
                )
                if attempt > MAX_RETRIES:
                    failures.append(
                        SceneClipBatchFailure(
                            scene_id=scene.id,
                            action_index=action_index,
                            attempts=attempt,
                            error=last_error,
                        )
                    )
                    upsert_scene_clip(
                        SceneClipRecord(
                            scene_id=scene.id,
                            action_index=action_index,
                            title=label,
                            category=scene.family.value,
                            action=action,
                            prompt="",
                            status=SceneClipStatus.FAILED,
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
        table.add_row("Est. spent", f"${estimate_i2v_cost(generated, duration_seconds):.2f}")
    console.print()
    console.print(table)

    if failures:
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        failure_path = config.LOGS_DIR / f"batch_scene_clip_failures_{timestamp}.json"
        failure_path.parent.mkdir(parents=True, exist_ok=True)
        failure_path.write_text(
            json.dumps([item.model_dump() for item in failures], indent=2),
            encoding="utf-8",
        )
        console.print(f"[red]Failures saved to:[/red] {failure_path}")

    return failures


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate I2V clips from master scenes using RunPod Kling."
    )
    parser.add_argument("--scene", help="Single scene id from scenes.json")
    parser.add_argument("--action-index", type=int, default=0)
    parser.add_argument("--action", help="Custom action text")
    parser.add_argument("--duration", type=int, default=5, choices=[5, 10])
    parser.add_argument("--phase2", action="store_true", help="Batch all pending scene clips")
    parser.add_argument(
        "--actions-per-scene",
        type=int,
        default=3,
        choices=[1, 2, 3],
        help="How many example_actions to generate per scene in batch mode",
    )
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--force", action="store_true")
    parser.add_argument("--limit", type=int)
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    if args.phase2:
        action_indices = list(range(args.actions_per_scene))
        failures = run_phase2_batch(
            dry_run=args.dry_run,
            force=args.force,
            limit=args.limit,
            scene_filter=args.scene,
            action_indices=action_indices,
            duration_seconds=args.duration,
        )
        if failures:
            sys.exit(1)
        return

    if not args.scene:
        console.print("Provide --scene <id> or --phase2")
        sys.exit(1)

    try:
        generate_scene_clip(
            args.scene,
            args.action_index,
            action=args.action,
            duration_seconds=args.duration,
            dry_run=args.dry_run,
            force=args.force,
        )
    except Exception as exc:
        console.print(f"[red]Failed:[/red] {exc}")
        sys.exit(1)


if __name__ == "__main__":
    main()
