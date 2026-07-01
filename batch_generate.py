import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from pydantic import BaseModel
from rich.console import Console

import config
from generate_clip import generate_clip
from library import find_completed_by_title_category

console = Console()

MAX_RETRIES = 2


class ClipSpec(BaseModel):
    title: str
    category: str
    tags: list[str]
    action: str


class BatchFailure(BaseModel):
    title: str
    category: str
    attempts: int
    error: str


def load_clip_specs(path: Path | None = None) -> list[ClipSpec]:
    specs_path = path or config.CLIP_SPECS_PATH
    raw = json.loads(specs_path.read_text(encoding="utf-8"))
    return [ClipSpec.model_validate(item) for item in raw]


def should_skip(spec: ClipSpec) -> bool:
    return find_completed_by_title_category(spec.title, spec.category) is not None


def run_batch(specs_path: Path | None = None) -> list[BatchFailure]:
    specs = load_clip_specs(specs_path)
    failures: list[BatchFailure] = []

    for spec in specs:
        if should_skip(spec):
            console.print(
                f"[dim]Skipping completed clip:[/dim] {spec.title} ({spec.category})"
            )
            continue

        console.print(f"[bold]Generating:[/bold] {spec.title} ({spec.category})")
        last_error = "Unknown error"

        for attempt in range(1, MAX_RETRIES + 2):
            try:
                record = generate_clip(
                    title=spec.title,
                    category=spec.category,
                    tags=spec.tags,
                    action=spec.action,
                )
                console.print(
                    f"[green]Completed:[/green] {record.title} -> {record.filename}"
                )
                last_error = ""
                break
            except Exception as exc:
                last_error = str(exc)
                console.print(
                    f"[yellow]Attempt {attempt} failed for {spec.title}:[/yellow] {exc}"
                )
                if attempt > MAX_RETRIES:
                    failures.append(
                        BatchFailure(
                            title=spec.title,
                            category=spec.category,
                            attempts=attempt,
                            error=last_error,
                        )
                    )

    if failures:
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        failure_path = config.LOGS_DIR / f"batch_failures_{timestamp}.json"
        failure_path.parent.mkdir(parents=True, exist_ok=True)
        payload = [item.model_dump() for item in failures]
        failure_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        console.print(f"[red]Batch failures saved to:[/red] {failure_path}")

    return failures


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Batch generate clips from data/clip_specs.json."
    )
    parser.add_argument(
        "--specs",
        type=Path,
        default=config.CLIP_SPECS_PATH,
        help="Path to clip specs JSON",
    )
    args = parser.parse_args()

    failures = run_batch(args.specs)
    if failures:
        console.print(f"[red]{len(failures)} clip(s) failed.[/red]")
        sys.exit(1)

    console.print("[green]Batch complete.[/green]")


if __name__ == "__main__":
    main()
