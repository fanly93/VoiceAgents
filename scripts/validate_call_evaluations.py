from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from voiceagents.call_evaluation import validate_dataset


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate VoiceAgents call evaluation data.")
    parser.add_argument("dataset", type=Path)
    args = parser.parse_args()

    with args.dataset.open("r", encoding="utf-8") as handle:
        dataset = json.load(handle)

    issues = validate_dataset(dataset)
    if issues:
        print(f"Validation failed: {len(issues)} issue(s)", file=sys.stderr)
        for issue in issues:
            print(f"- {issue.call_id} {issue.field}: {issue.message}", file=sys.stderr)
        return 1

    print(f"Validation passed: {args.dataset}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
