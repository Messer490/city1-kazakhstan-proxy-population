from __future__ import annotations

import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from city1.llm_tools import generate_evidence_pack, get_city_summary


def main() -> int:
    print("Full V3 example: Almaty")
    print(json.dumps(generate_evidence_pack("Almaty", mode="city_brief"), indent=2, ensure_ascii=False))
    print()
    print("Limited-support example: Kurchatov")
    print(json.dumps(get_city_summary("Kurchatov"), indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
