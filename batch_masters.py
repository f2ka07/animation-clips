"""Phase 1: batch-generate all missing master scene images."""

import sys

from generate_master import run_phase1_batch


def main() -> None:
    failures = run_phase1_batch()
    if failures:
        sys.exit(1)


if __name__ == "__main__":
    main()
