from __future__ import annotations

import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from city1.llm_fallback import generate_fallback_response  # noqa: E402


def _print_example(title: str, payload: dict) -> None:
    print(f"\n=== {title} ===")
    print(json.dumps(payload, indent=2, ensure_ascii=False))


def main() -> int:
    _print_example(
        "Almaty city brief",
        generate_fallback_response(city="Almaty", mode="city_brief"),
    )
    _print_example(
        "Kurchatov limited-support brief",
        generate_fallback_response(city="Kurchatov", mode="city_brief"),
    )
    _print_example(
        "Dangerous claim pre-check",
        generate_fallback_response(
            question="City1 reconstructs true census counts and identifies verified hotspots.",
            mode="claim_checker",
        ),
    )
    _print_example(
        "Full V3 city comparison",
        generate_fallback_response(mode="compare_cities"),
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
