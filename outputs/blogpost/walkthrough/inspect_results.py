"""Inspect a complete result file without model requests or trace uploads."""
import argparse
import json
from pathlib import Path

from drug_discovery import print_report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("file", type=Path)
    args = parser.parse_args()
    rows = json.loads(args.file.read_text(encoding="utf-8-sig"))
    if not isinstance(rows, list) or not rows:
        parser.error("Expected a nonempty list of result records.")
    trials = {row.get("trial", 1) for row in rows}
    if any(type(trial) is not int or trial < 1 for trial in trials):
        parser.error("Trial identifiers must be positive integers.")
    modes = {row.get("mode", "demo") for row in rows}
    if len(modes) != 1 or not modes <= {"demo", "comparison"}:
        parser.error("Expected one valid mode per file.")
    try:
        gate = print_report(rows, repeats=max(trials), mode=modes.pop())
    except (ValueError, TypeError) as error:
        parser.error(f"Incomplete or invalid scored run: {error}")
    for row in rows:
        print(f"\n{row['version']} trial {row.get('trial', 1)}")
        print("Answer:", row["answer"])
        print("Judge reason:", row["reason"])
    return 0 if gate["passed"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
