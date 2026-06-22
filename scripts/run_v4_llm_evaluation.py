from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from city1.llm_evaluation import DEFAULT_CONFIGS, run_evaluation  # noqa: E402


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run the offline-capable City1 v4 interpretation evaluation benchmark."
    )
    parser.add_argument("--question-bank", default="data/v4_eval/question_bank.csv")
    parser.add_argument("--output-dir", default="reports/v4_llm_evaluation")
    parser.add_argument("--max-questions", type=int, default=None)
    parser.add_argument(
        "--configs",
        default=",".join(DEFAULT_CONFIGS),
        help="Comma-separated configs: fallback_only,gemini_with_fallback,fallback_with_cache,claim_checker_only.",
    )
    parser.add_argument("--no-gemini", action="store_true", help="Record Gemini as requested but prevent API calls.")
    parser.add_argument("--no-cache", action="store_true", help="Disable cache behavior in every configuration.")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    names = [name.strip() for name in args.configs.split(",") if name.strip()]
    configs = []
    for name in names:
        if name not in DEFAULT_CONFIGS:
            raise SystemExit(f"Unknown config: {name}")
        config = dict(DEFAULT_CONFIGS[name])
        if args.no_gemini and config.get("provider") == "gemini":
            config["disable_gemini"] = True
        if args.no_cache:
            config["use_cache"] = False
        configs.append(config)
    result = run_evaluation(
        question_bank_path=args.question_bank,
        configs=configs,
        output_dir=args.output_dir,
        max_questions=args.max_questions,
    )
    print(json.dumps({
        "question_count": min(
            result["question_bank_validation"]["question_count"],
            args.max_questions if args.max_questions is not None else result["question_bank_validation"]["question_count"],
        ),
        "configs": result["configs"],
        "summary": result["summary"],
        "output_files": result["output_files"],
    }, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
