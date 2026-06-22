from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Compatibility wrapper for building the City1 v3 paper-facing evidence package."
    )
    parser.add_argument(
        "--run-id",
        type=str,
        default="city1_v3_rf500m_e20_20260618T040646Z",
        help="Frozen v3 run id to package.",
    )
    return parser


def _git_commit(root: Path) -> str | None:
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"],
            cwd=root,
            check=True,
            capture_output=True,
            text=True,
        )
    except Exception:
        return None
    return result.stdout.strip() or None


def main() -> None:
    root = Path(__file__).resolve().parents[1]
    if str(root) not in sys.path:
        sys.path.insert(0, str(root))

    from src.city1.paper_report_v3 import PaperReportV3Config, build_paper_v3_uncertainty_package

    parser = build_parser()
    args = parser.parse_args()

    outputs = build_paper_v3_uncertainty_package(
        PaperReportV3Config(
            run_id=args.run_id,
            git_commit=_git_commit(root),
            python_version=sys.version.split()[0],
        )
    )
    print("City1 v3 paper-facing package completed.")
    for name, path in outputs.items():
        print(f"  - {name}: {path}")


if __name__ == "__main__":
    main()
