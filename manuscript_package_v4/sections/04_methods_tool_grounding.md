# 4. Methods: Local Tools and Evidence Grounding

The tool layer exposes city summaries, hotspot summaries, confidence summaries, uncertainty summaries, selected-cell evidence, city comparisons, claim boundaries, and method summaries. `generate_evidence_pack` combines only the fields needed for a requested mode and records both evidence sources and missing artifacts.

Full uncertainty-aware interpretation is available for Almaty, Astana, Semey, and Shymkent. Basic or partial cities receive explicitly reduced support. Unknown cities return a bounded unavailable-evidence response rather than fabricated values. The language layer receives a compact representation and cannot access raw files, secrets, or unrestricted internet sources.
