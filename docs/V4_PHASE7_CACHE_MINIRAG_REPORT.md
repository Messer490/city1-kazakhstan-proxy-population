# City1 v4 Phase 7 - Cache and Mini-RAG Report

## Status and purpose

Phase V4.7 is complete. City1 v4 now has a local safe-answer cache and a deterministic City1-only retrieval layer that reduces repeated provider calls and exposes compact supporting snippets.

The cache and mini-RAG layer does not create new population evidence. It only reuses previously safe answers and retrieves compact snippets from existing City1 artifacts. It improves robustness, cost control, repeatability, and evidence visibility, but it does not improve population prediction accuracy.

## Implemented files

- `src/city1/llm_cache.py` - stable hashing, cache storage/lookup, local corpus construction, retrieval, and evidence-pack augmentation.
- `tests/test_llm_cache.py` - isolated cache and retrieval tests using temporary directories.
- `docs/V4_PHASE7_CACHE_MINIRAG_REPORT.md` - this implementation record.

Modified:

- `src/city1/llm_client.py` - retrieval-before-generation, cache-before-provider, safe storage-after-guardrail, and cache-hit provider path.
- `app_v4.py` - cache/retrieval controls, status, metadata, snippets, and report integration.
- `tests/test_llm_client.py` - explicit cache isolation for provider tests.
- `tests/test_app_v4_smoke.py` - provider/cache compatibility.
- `.gitignore` - runtime cache exclusions.

No frozen V2/V3 output, report, model, evidence table, or manuscript result was modified.

## Cache storage layout

Default runtime directory:

```text
data/v4_qa_cache/
```

Runtime contents:

```text
cache_index.jsonl
cached_answers/<cache_id>.json
```

The directory and `*.cache.json` files are excluded from version control. Tests use `TemporaryDirectory` and do not create project cache entries.

## Cache entry schema

Each index entry records:

- deterministic `cache_id`;
- UTC creation time;
- normalized and original question;
- city, mode, and language;
- requested and used provider;
- stable evidence and response hashes;
- guardrail pass and severity;
- safe final answer;
- evidence and claim-boundary notes;
- missing-artifact state;
- answer source (`fallback` or `guarded_gemini`);
- schema version `v4_cache_1`.

The cached-answer file stores only a selected safe response schema. It excludes API keys, environment variables, authorization fields, raw Gemini text, raw project files, and provider secrets.

## Safety and stale-answer control

A response is stored only when:

- guardrail passed;
- severity is `none` or `low`;
- current structured response validation passes;
- answer and `evidence_used` are non-empty;
- no secret/raw field is present.

Cache lookup requires the same:

- city;
- mode;
- language;
- stable evidence hash.

The evidence hash excludes question-specific retrieval metadata but includes the scientific evidence packet. A changed evidence packet therefore prevents silent reuse of an older answer.

Exact normalized-question lookup runs first. Optional lexical similarity uses `difflib.SequenceMatcher` with a conservative threshold and only within the same evidence context. Every loaded cached answer is rechecked against the current guardrail and grounding rules before use.

## Mini-RAG design

The retrieval corpus is built locally from:

- claim boundaries;
- method summary;
- all city summaries;
- full-V3 hotspot summaries;
- confidence-band summaries;
- uncertainty summaries;
- V4 documentation;
- frozen V3 limitation files.

The current corpus contains 38 compact entries. Entries retain title, short text, local source, city, and category.

Retrieval uses:

1. normalized exact phrase matching;
2. token overlap;
3. deterministic `difflib` similarity.

No web search, Google Search grounding, external vector database, or internet RAG is used. Retrieval results are limited to ten, and evidence-pack augmentation defaults to five snippets.

## Client integration flow

`generate_llm_response` now accepts:

- `use_cache=True`
- `use_retrieval=True`
- `cache_dir=None`

Execution order:

1. build or accept the local evidence packet;
2. optionally add City1-only snippets;
3. compute evidence hash and lookup safe cache;
4. return `provider_used="cache"` on a valid hit;
5. otherwise call Gemini or deterministic fallback;
6. run deterministic claim-boundary guardrails;
7. store only a safe final response;
8. return cache and retrieval metadata.

On a cache hit, Gemini is not called. The response records match type, similarity, cache ID, shortened/displayable evidence hash, original safe source, and reason.

## Streamlit integration

The sidebar now includes:

- `Use local cache` checkbox;
- `Use City1 mini-RAG snippets` checkbox;
- `Show cache status` button.

The main response view displays:

- cache hit/miss;
- exact/similarity match type;
- similarity score;
- shortened evidence hash;
- cache reuse notice;
- `Retrieved City1 evidence snippets` expander.

The Markdown report includes provider metadata, guardrail audit, cache metadata, evidence hash, and retrieved snippets. Clearing the answer does not delete cache files; no destructive clear-cache action was added.

## API quota relevance

Repeated safe questions can be answered from the local cache before a Gemini call. This reduces quota consumption and preserves usability when quota or network access is limited. Because cached answers remain evidence-hash-bound and guardrail-revalidated, quota savings do not bypass scientific claim controls.

## Tests

Compilation:

```powershell
python -m py_compile src\city1\llm_cache.py
python -m py_compile src\city1\llm_client.py
python -m py_compile app_v4.py
```

Cache tests:

```powershell
python -m unittest tests.test_llm_cache -v
```

Result: 11 tests passed.

Coverage includes:

- question normalization;
- stable evidence hash;
- deterministic cache key;
- safe response storage;
- exact lookup;
- critical-response rejection;
- nested cache-directory creation;
- offline corpus construction;
- confidence/probability retrieval;
- compact evidence augmentation;
- second-call `provider_used="cache"` behavior;
- JSON serialization.

Provider and app regression suites also pass with cache explicitly isolated or disabled. Headless Streamlit verification confirmed:

- three expected checkboxes;
- cache-status button;
- zero UI exceptions;
- cache-disabled generation;
- cache metadata in Markdown;
- no project cache directory created during verification.

## Known limitations

- Similarity matching is lexical, not semantic.
- A high similarity threshold intentionally favors safety over cache hit rate.
- Corpus construction reads local summaries/documents at request time and is not yet persisted as a vector index.
- Empty questions may return no retrieval snippets.
- Cache invalidation depends on deterministic evidence serialization and schema version.
- Runtime cache writes are local and do not provide multi-user locking beyond atomic file replacement.
- Cache reuse improves cost and repeatability, not scientific accuracy.

## Exact next phase

V4.8 - build a frozen evaluation benchmark comparing deterministic fallback, optional Gemini, cache reuse, retrieval visibility, and guarded final answers across safe, ambiguous, missing-evidence, and adversarial questions.
