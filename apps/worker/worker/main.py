from __future__ import annotations

import argparse
import json

from .scheduler import process_pending_tasks


def main() -> None:
    parser = argparse.ArgumentParser(description="StableGPU worker")
    parser.add_argument("--limit", type=int, default=5, help="Max tasks to process")
    args = parser.parse_args()
    result = process_pending_tasks(limit=args.limit)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
