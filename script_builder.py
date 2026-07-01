import argparse
import json
import sys

from rich.console import Console

from prompts import (
    ALLOWED_PROPS,
    BEAT_TYPES,
    EVERYDAY_SETTINGS,
    build_action,
    validate_action,
)

console = Console()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Build a clip action sentence and JSON spec snippet."
    )
    parser.add_argument("--title", required=True)
    parser.add_argument("--category", required=True)
    parser.add_argument("--tags", required=True, help="Comma-separated tags")
    parser.add_argument("--setting", required=True, choices=EVERYDAY_SETTINGS)
    parser.add_argument("--beat", required=True, choices=BEAT_TYPES)
    parser.add_argument("--motion", required=True, help="What the figure does")
    parser.add_argument(
        "--emotion-change",
        default="",
        help="How expression or posture changes by the end",
    )
    parser.add_argument(
        "--props",
        default="",
        help=f"Comma-separated props from: {', '.join(ALLOWED_PROPS)}",
    )
    parser.add_argument("--duration", type=int, default=5, choices=[5, 6, 10])
    parser.add_argument("--actors", type=int, default=1, choices=[1, 2])
    parser.add_argument(
        "--subject",
        default="A stick figure",
        help='Use "Two stick figures" when actors=2',
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    props = [item.strip() for item in args.props.split(",") if item.strip()]

    action = build_action(
        setting=args.setting,
        beat=args.beat,
        subject=args.subject,
        props=props,
        motion=args.motion,
        emotion_change=args.emotion_change,
        actors=args.actors,
    )

    warnings = validate_action(action)
    for warning in warnings:
        console.print(f"[yellow]Warning:[/yellow] {warning}")

    spec = {
        "title": args.title,
        "category": args.category,
        "tags": [tag.strip() for tag in args.tags.split(",") if tag.strip()],
        "beat": args.beat,
        "setting": args.setting,
        "duration_seconds": args.duration,
        "action": action,
    }

    console.print("[bold]Action[/bold]")
    console.print(action)
    console.print()
    console.print("[bold]clip_specs.json entry[/bold]")
    console.print(json.dumps(spec, indent=2))
    console.print()
    console.print("[bold]generate command[/bold]")
    tags = ",".join(spec["tags"])
    console.print(
        f'python generate_clip.py --title "{args.title}" --category "{args.category}" '
        f'--tags "{tags}" --duration {args.duration} '
        f'--action "{action}"'
    )

    if warnings:
        sys.exit(2)


if __name__ == "__main__":
    main()
