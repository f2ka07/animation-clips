import argparse
import sys

from rich.console import Console

import config
from library import (
    ClipRecord,
    ClipStatus,
    add_clip,
    build_output_filename,
    find_failed_by_title_category,
    update_clip,
)
from prompts import NEGATIVE_PROMPT, build_prompt, normalize_duration
from providers import VideoProviderError, create_video_provider

console = Console()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Generate a single stick figure psychology clip via the configured video provider."
    )
    parser.add_argument("--title", required=True, help="Clip title")
    parser.add_argument("--category", required=True, help="Clip category")
    parser.add_argument(
        "--tags",
        required=True,
        help="Comma-separated tags, e.g. delay,work,phone",
    )
    parser.add_argument(
        "--action",
        required=True,
        help="Scene action description for the stick figure animation",
    )
    parser.add_argument(
        "--duration",
        type=int,
        default=config.DURATION,
        help="Clip duration in seconds (5-10)",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=config.SEED,
        help="Random seed (-1 for random)",
    )
    return parser.parse_args()


def parse_tags(raw: str) -> list[str]:
    return [tag.strip() for tag in raw.split(",") if tag.strip()]


def generate_clip(
    title: str,
    category: str,
    tags: list[str],
    action: str,
    seed: int | None = None,
    duration_seconds: int | None = None,
) -> ClipRecord:
    resolved_duration = normalize_duration(
        config.DURATION if duration_seconds is None else duration_seconds
    )
    prompt = build_prompt(action, duration_seconds=resolved_duration)
    negative_prompt = NEGATIVE_PROMPT
    resolved_seed = config.SEED if seed is None else seed

    existing_failed = find_failed_by_title_category(title, category)
    if existing_failed:
        record = existing_failed.model_copy(
            update={
                "prompt": prompt,
                "negative_prompt": negative_prompt,
                "seed": resolved_seed,
                "status": ClipStatus.PENDING,
            }
        )
        update_clip(record)
    else:
        record = ClipRecord(
            title=title,
            category=category,
            tags=tags,
            prompt=prompt,
            negative_prompt=negative_prompt,
            duration_seconds=resolved_duration,
            width=config.WIDTH,
            height=config.HEIGHT,
            fps=config.FPS,
            steps=config.STEPS,
            cfg=config.CFG,
            seed=resolved_seed,
            status=ClipStatus.PENDING,
        )
        add_clip(record)

    record.status = ClipStatus.RUNNING
    update_clip(record)

    input_payload = config.build_generation_payload(
        prompt=prompt,
        negative_prompt=negative_prompt,
        seed=resolved_seed,
        duration_seconds=resolved_duration,
    )

    provider = create_video_provider()
    filename = build_output_filename(category, title)
    output_path = config.OUTPUT_DIR / filename

    try:
        output = provider.generate(input_payload)
        provider.save_video(output, output_path)
        record.filename = filename
        record.status = ClipStatus.COMPLETED
        update_clip(record)
        return record
    except (VideoProviderError, Exception) as exc:
        record.status = ClipStatus.FAILED
        update_clip(record)
        raise exc


def main() -> None:
    args = parse_args()
    tags = parse_tags(args.tags)

    try:
        record = generate_clip(
            title=args.title,
            category=args.category,
            tags=tags,
            action=args.action,
            seed=args.seed,
            duration_seconds=args.duration,
        )
    except Exception as exc:
        console.print(f"[red]Generation failed:[/red] {exc}")
        sys.exit(1)

    saved_path = config.OUTPUT_DIR / record.filename
    console.print(f"[green]Saved clip:[/green] {saved_path}")
    console.print(f"[green]Clip id:[/green] {record.id}")


if __name__ == "__main__":
    main()
