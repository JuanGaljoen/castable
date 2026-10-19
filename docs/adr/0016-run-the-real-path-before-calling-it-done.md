# 16. Run the real path before calling vision, shape or UI work done

- **Status:** Accepted
- **Date:** 2026-10-19 (lessons from 2026-07-21 onwards)
- **Context ticket:** RNG-23 (stone shape), RNG-24 (composable features),
  RNG-19 (geometry refinement); generalises ADR-0004 decision 3.

## Context

ADR-0004 established that a feature calling an external API is not verified
until it has run against the real API once. The same failure shape kept turning
up well beyond external APIs. A fully green suite was hiding defects that only
the real user path showed:

- **RNG-23.** Bugs passed a green 3413-test suite and were caught by a real photo
  and a screenshot. One of them: the *default* ring style silently discarded the
  chosen stone shape, because solitaire still took the legacy flat-7 request path
  (`from_params`), which has no `stones.shape` (fixed in 43abe6b by sending
  solitaire as a structured spec). Another was a gate still measuring the short
  axis of an oval (ADR-0006). Every test had been written against the author's
  assumptions rather than against what a user gets.
- **RNG-24.** The first real upload after CP3 returned a 500 behind 3900 green
  tests, because the spec poisoned itself passing back through its own
  validator (ADR-0013). Every fixture had at most one feature; the real photo
  had two.
- **RNG-19.** Four real geometry defects sat behind a green 3488-test suite. None
  was found by a test; every one was found by comparing a render against a trade
  reference sketch (`docs/reference/`, ADR-0008).

Running the real path has its own trap. **The Flask dev server runs with reload
off** (`python wsgi.py` -> `app.run()`), so after an edit it keeps serving the old
code. In RNG-19 a before/after twice reported "unchanged" before the real result
appeared, and a `pkill` that reported success had left the process alive on port
5000 (`specs/RNG-19.md`, CP1 process note). "I see no change" was a stale
process, not a bad build.

## Decision

**Vision, stone-shape, geometry-appearance and UI work is not done until the
real path has run**, on top of the suite:

- vision and spec work: the fidelity probe (`python probes/fidelity_probe.py`)
  or a real upload through the dev server;
- geometry appearance: a render judged against the `docs/reference/` sketch for
  that archetype or cut;
- UI behaviour: a real browser against the dev server (the zero-install
  playwright path in `CLAUDE.md`).

**Before trusting a before/after on the dev server, confirm the server process
is younger than the edit.**

## Consequences

- Stub-only and source-inspection tests stay necessary. They are just not the
  evidence for these kinds of change.
- The probe costs real API calls (one per photo, about 2 cents for the corpus),
  which is cheap next to a defect that ships behind a green suite.
