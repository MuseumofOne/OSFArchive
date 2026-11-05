"""Prevent an incomplete source reconciliation from replacing the live archive.

A complete, verified empty source is valid: it applies confirmed withdrawals.
A suspended, missing or malformed reconciliation must leave Pages unchanged.
"""

import argparse
import json
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "report", nargs="?", type=Path, default=Path(".sync-work/report.json")
    )
    args = parser.parse_args()
    try:
        report = json.loads(args.report.read_text())
    except (OSError, ValueError):
        raise SystemExit(
            "Publication stopped: reconciliation report is unavailable or invalid."
        )
    if not isinstance(report, dict) or report.get("mode") != "apply":
        raise SystemExit(
            "Publication stopped: source reconciliation is incomplete; retain the last successful deployment."
        )
    print("Complete source reconciliation verified for publication.")


if __name__ == "__main__":
    main()
