# 4. Structured-output schemas must have all-required fields; stub-only tests hide this

- **Status:** Accepted
- **Date:** 2026-07-13
- **Context ticket:** RNG-21 (enable the vision layer end-to-end with a real key).

## Context

The vision layer (RNG-6 classification, RNG-12 photo → RingSpec) was built and "verified" entirely
against a stubbed Anthropic client — every test monkeypatches `ringcad.classify.anthropic.Anthropic`,
so the structured-output schema (`RingClassification`) was never once sent to the real Messages API.
It shipped through four tickets looking green.

The first real API call, on RNG-21, failed immediately. Two failure modes, one root cause:

1. **Hard reject (400):** `Schemas contains too many parameters with union types (17 parameters with
   type arrays or anyOf)... exponential compilation cost... limit: 16.` The `RingClassification`
   fields were `float | None`, and each nullable field compiles to an `anyOf` union.
2. **After cutting the unions to 1 (sentinel `0.0` defaults instead of `| None`), the call HUNG** and
   timed out at 30s, then 60s, then 90s — even on a text-only prompt with a small image. A plain
   `messages.create` returned in 0.9s; a trivial 1-field `messages.parse` returned in 1.9s. Bisecting
   the schema showed the trigger: **16 *defaulted* (optional) float fields hang; 16–24 *required*
   float fields parse fine in 4–7s.**

The through-line: strict structured output treats any field carrying a default as **optional**, and a
schema with many optional fields makes the server-side compiler consider an exponential number of
present/absent field combinations. Nullable `anyOf` unions were just the first, louder symptom of the
same "too many optional shapes" cost — removing the unions but leaving the fields optional (via `0.0`
defaults) swapped a fast 400 for a silent hang.

Neither symptom is reachable offline against a stub. The stub returns whatever `RingClassification`
instance the test hands it; it never compiles the schema, so no test could see either failure.

## Decision

**1. Every field in a structured-output (`messages.parse` / `output_format`) schema is required — no
defaults.** Model the "not provided" case with an in-band sentinel the parser interprets, not with an
optional field:

- Numeric estimate fields are required `float`; **`0` means "not estimated"** (every real dimension is
  strictly positive), and parsing treats `0` as absent and falls back to the shared/group default.
- The system prompt instructs the model to fill every field and use `0` for any dimension it cannot
  estimate or that does not apply to the chosen archetype.
- This also keeps union/array params near zero as a side effect (only `features: list[str]` remains),
  so the 16-union cap is never approached.

**2. Guard the schema shape offline.** `tests/test_classify_schema.py` asserts, on the generated JSON
schema, that (a) there are **zero optional fields** (the load-bearing rule) and (b) union/array params
stay within the 16 cap. These are the tests that would have caught the bug without a key.

**3. A feature that calls an external API is not "verified" until it has run against the real API
once.** Stub-only green is necessary, not sufficient. Schema-compilation, auth, and latency live only
on the real path.

## Consequences

- `RingClassification` and `RingConfidence` have no field defaults; test constructors supply a full
  field set via helpers (`_FULL`, `_conf`).
- Live behaviour confirmed on a real solitaire photo: correct archetype, correct 4-prong, five
  estimable dimensions adjusted, ~4s latency, coherent per-field confidence (0.60–0.95, lowest on the
  hardest-to-see field, `band_thickness`). Decisions recorded for RNG-21: keep **Haiku** as the
  default model, keep the **0.5** confidence-marker threshold.
- Future structured-output schemas (new archetype groups, new vision fields) must stay all-required
  and are covered by the offline guard; adding an optional field will fail the suite, not the next
  real call.
- Any future external-API feature should include at least one real-call smoke check as part of Verify,
  not defer the first real call to a follow-up ticket.
