# City1 v4 LLM Assistant Plan

## Scientific motivation

City1 v4 is not a new population model. It is an interpretation assistant for frozen V2/V3 artifacts.

The scientific need is practical: the calibrated proxy surface and uncertainty layer are already useful, but a user still needs help reading them safely. A tool-grounded LLM can improve:

- interpretability;
- evidence linking;
- city-to-city comparison;
- hotspot and uncertainty explanation;
- claim-boundary discipline.

The assistant exists to explain frozen evidence, not to create new evidence.

## Role relative to V2 and V3

- V2 builds the deterministic calibrated proxy population surface.
- V3 adds uncertainty-aware interpretation around that surface.
- V4 sits on top of V2/V3 and only explains their frozen outputs.

V4 must not:

- retrain any model;
- modify P10/P50/P90;
- modify confidence scores;
- create new hotspot classes;
- create new population estimates;
- claim improved prediction accuracy.

## Proposed architecture

The planned architecture is evidence-first and tool-grounded:

1. user asks a question in Streamlit;
2. the app gathers frozen evidence through local tools;
3. the evidence pack is passed to either Gemini or a deterministic fallback;
4. a guardrail checker blocks unsafe claims;
5. the answer is returned with evidence used and claim-boundary notes;
6. the answer can be cached for repeated use.

## Streamlit-first decision

Streamlit should be the first user-facing layer because it is the fastest way to make the assistant usable on top of existing V2/V3 artifacts.

The app should remain a thin interface over local evidence tools. It should not become the source of scientific truth.

## Gemini + fallback design

V4 should support two answer paths:

- Gemini API for richer language generation when an API key is available;
- deterministic fallback when Gemini is unavailable, rate-limited, or disabled.

The fallback is not a failure state. It is part of the design because it proves the assistant is tool-grounded and evidence-first, not dependent on uncontrolled generation.

## City1 Evidence RAG concept

V4 uses a local, closed-world evidence retrieval design:

- retrieve from frozen City1 artifacts only;
- do not use internet RAG;
- do not browse external sources;
- do not expand geography beyond the frozen Kazakhstan scope.

This is best understood as City1 Evidence RAG: retrieval over local project evidence, not open-web retrieval.

## Scope boundaries

V4 will support interpretation only.

It will not:

- extend the geography;
- change the underlying model;
- alter validation results;
- invent city evidence not present in frozen outputs;
- replace scientific review.

## Future work

Future FastAPI or custom frontend work is possible later, but it is optional and outside Phase 1. Streamlit remains the initial implementation choice.

