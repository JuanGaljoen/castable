# RNG-21 — Enable the vision layer end-to-end (configure key + verify real photos)

**Type:** feature · **Landed:** 2026-07-13 · *Written after the fact from the project
record; there was no frozen design.*

## Problem

The vision layer (RNG-6, RNG-12) had only ever run against a stubbed client. Turn
it on with a real API key and verify it on real photos.

## Outcome

**Shipped.** `.env` loads at startup via `python-dotenv` (`load_dotenv()` in
`create_app()`; explicit exports still win). Verified live on a real solitaire
photo: correct archetype and 4 prongs, five estimable dims adjusted, ~4s per call,
confidence 0.60-0.95.

**Decisions recorded.** Keep Haiku as the default model; keep the 0.5
confidence-marker threshold.

**What surprised us.** The `RingClassification` structured-output schema had ~24
*optional* (defaulted) fields. The real Messages API rejected it (400 on
`float | None` unions) and then, once the unions were cut, *hung* on it (exponential
compile cost from the present/absent field combinations). Fix: **every schema field
is required, no defaults**; `0` is the "not estimated" sentinel the parser reads, and
the prompt tells the model to fill every field. Offline guard:
`tests/test_classify_schema.py` asserts zero optional fields + the 16-union cap.
Because every classify test stubbed the client, the bug shipped invisibly through
RNG-6 and RNG-12.

**ADRs it left.** docs/adr/0004 (structured-output schemas need all-required fields;
verify against the real API once).
