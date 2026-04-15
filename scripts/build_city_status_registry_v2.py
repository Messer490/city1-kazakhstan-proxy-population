from __future__ import annotations

import sys
from pathlib import Path


def main() -> None:
    root = Path(__file__).resolve().parents[1]
    if str(root) not in sys.path:
        sys.path.insert(0, str(root))

    from src.city1.city_status import DEFAULT_STATUS_CSV, build_city_status_registry

    frame = build_city_status_registry()
    DEFAULT_STATUS_CSV.parent.mkdir(parents=True, exist_ok=True)
    frame.to_csv(DEFAULT_STATUS_CSV, index=False)

    print(f"Saved city status registry: {DEFAULT_STATUS_CSV}")
    print(
        "Summary: "
        f"official_total_available={int(frame['official_total_available'].sum())}, "
        f"validated_batch={int(frame['validated_batch'].sum())}, "
        f"smoke_passed={int(frame['smoke_passed'].sum())}, "
        f"saved_inference_example={int(frame['saved_inference_example'].sum())}"
    )
    print(frame.to_string(index=False))


if __name__ == "__main__":
    main()
