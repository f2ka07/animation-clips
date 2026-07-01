import argparse
import json
import sys

from rich.console import Console
from rich.table import Table

from scenes import (
    SceneFamily,
    build_i2v_animation_prompt,
    build_master_image_prompt,
    find_scene,
    load_scenes,
    master_image_path,
    scenes_by_family,
    scenes_by_tag,
)
from prompts import NEGATIVE_PROMPT

console = Console()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="List reusable master scenes and build controlled image/I2V prompts."
    )
    parser.add_argument("--list", action="store_true", help="List all scenes")
    parser.add_argument("--family", choices=[item.value for item in SceneFamily])
    parser.add_argument("--tag", help="Filter scenes by reuse tag")
    parser.add_argument("--scene", help="Scene id, e.g. office_two_people_meeting")
    parser.add_argument(
        "--image-prompt",
        action="store_true",
        help="Print master still-image prompt for API image generation",
    )
    parser.add_argument(
        "--animation-prompt",
        help="Print I2V animation prompt for an action sentence",
    )
    parser.add_argument("--duration", type=int, default=6, choices=[5, 6, 10])
    parser.add_argument("--json", action="store_true", help="Output scene record as JSON")
    return parser.parse_args()


def print_scene_table(scenes: list) -> None:
    table = Table(show_header=True, header_style="bold")
    table.add_column("ID")
    table.add_column("Family")
    table.add_column("Title")
    table.add_column("Actors")
    table.add_column("Master file")
    for scene in scenes:
        table.add_row(
            scene.id,
            scene.family.value,
            scene.title,
            str(scene.actor_count),
            scene.master_filename,
        )
    console.print(table)
    console.print(f"Total scenes: {len(scenes)}")


def main() -> None:
    args = parse_args()

    if args.list or args.family or args.tag:
        if args.family:
            scenes = scenes_by_family(args.family)
        elif args.tag:
            scenes = scenes_by_tag(args.tag)
        else:
            scenes = load_scenes()
        print_scene_table(scenes)
        return

    if not args.scene:
        console.print("Use --list, --family, --tag, or --scene <id>")
        sys.exit(1)

    scene = find_scene(args.scene)
    if scene is None:
        console.print(f"[red]Scene not found:[/red] {args.scene}")
        sys.exit(1)

    if args.json:
        console.print(json.dumps(scene.model_dump(mode="json"), indent=2))
        return

    console.print(f"[bold]{scene.title}[/bold] ({scene.id})")
    console.print(f"Family: {scene.family.value}")
    console.print(f"Actors: {scene.actor_count}  Supporting: {scene.supporting_figures}")
    console.print(f"Master: {master_image_path(scene)}")
    console.print(f"Tags: {', '.join(scene.reuse_tags)}")
    console.print()
    console.print("[bold]Example actions[/bold]")
    for item in scene.example_actions:
        console.print(f"- {item}")
    console.print()

    if args.image_prompt or not args.animation_prompt:
        console.print("[bold]Master image prompt[/bold]")
        console.print(build_master_image_prompt(scene))
        console.print()
        console.print("[bold]Negative prompt[/bold]")
        console.print(NEGATIVE_PROMPT)
        console.print()

    if args.animation_prompt:
        console.print("[bold]I2V animation prompt[/bold]")
        console.print(
            build_i2v_animation_prompt(
                scene,
                args.animation_prompt,
                duration_seconds=args.duration,
            )
        )


if __name__ == "__main__":
    main()
