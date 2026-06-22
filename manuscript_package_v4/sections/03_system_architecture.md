# 3. System Architecture

A user selects a supported mode and submits a city, cell, comparison, or claim question. Local tools read frozen V2/V3 summaries and construct a compact evidence packet. The local retrieval layer may add City1-only snippets, and the cache may reuse a previously guarded answer when the evidence hash and request match. The provider layer then uses deterministic fallback or optional Gemini generation. Every output passes deterministic claim and grounding checks before display.

The architecture deliberately separates evidence acquisition, language generation, and safety validation. This prevents provider availability from changing the underlying evidence and keeps V4 subordinate to the frozen analytical layers.
