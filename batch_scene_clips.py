"""Phase 2: batch-animate all master scenes via Kling I2V."""

import argparse
import sys

from generate_scene_clip import run_phase2_batch


def main() -> None:
    parser = argparse.ArgumentParser(description="Batch I2V clips from master scenes.")
    parser.add_argument(
        "--actions-per-scene",
        type=int,
        default=3,
        choices=[1, 2, 3],
        help="Example actions per scene (default: all 3)",
    )
    parser.add_argument("--duration", type=int, default=5, choices=[5, 10])
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--force", action="store_true")
    parser.add_argument("--limit", type=int)
    parser.add_argument("--scene", help="Limit batch to one scene id")
    args = parser.parse_args()

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


if __name__ == "__main__":
    main()
