# V4 Reproducibility Checklist

- [ ] Install the project dependencies in an isolated environment.
- [ ] Run the complete tests: `python -m unittest discover -s tests -v`.
- [ ] Run focused V4 tests: `python -m unittest tests.test_llm_evaluation tests.test_llm_cache tests.test_llm_client tests.test_llm_guardrails tests.test_llm_fallback tests.test_app_v4_smoke -v`.
- [ ] Launch the application: `streamlit run app_v4.py`.
- [ ] Run fallback-safe evaluation: `python scripts/run_v4_llm_evaluation.py --no-gemini`.
- [ ] Optionally run Gemini evaluation after setting a local environment variable: `python scripts/run_v4_llm_evaluation.py --configs fallback_only,gemini_with_fallback,claim_checker_only --max-questions 20`.
- [ ] Regenerate this package: `python scripts/build_v4_paper_package.py`.
- [ ] Confirm no `.env`, API key, runtime cache, or frozen V2/V3 file entered the package.
- [ ] Confirm the reported question/case counts match `reports/v4_llm_evaluation/`.
- [ ] Preserve the statement that evaluation concerns interpretation and claim discipline, not population accuracy.
