# 10. A passing test can be silent too — trace what it actually exercised, not just that it went green

- **Status:** Accepted
- **Date:** 2026-08-16
- **Context ticket:** RNG-32 (vision estimates fields independently, producing specs the casting
  gate rejects)

## Context

This repo has three prior ADRs about a *wrong* gate being silent: ADR-0005 (a fuse that drops
bodies still reports watertight), ADR-0006 (three consumers kept measuring the wrong axis and
nothing complained), ADR-0007 (a valid B-rep can still tessellate into a cracked mesh). All three
are the same shape — code that is wrong but produces no red anywhere, found only by comparing
real output against an independent source of truth (a render against a reference sketch, a real
photo against the endpoint).

RNG-32's Verify pass found the same shape one level up, in a test written for this ticket, in the
same session, by the same author who wrote the code it was testing.

`ClassifyResult._coherent_spec`'s fallback chain (detected archetype repaired → solitaire
repaired → pure defaults) needed a regression test proving the chain still returns a castable
spec on a genuinely infeasible input, not merely on a mocked one. A real infeasible input existed
— see ADR-0009's `min_prong_tip`/`stone_exceeds_bore` conflict — so a test was written that
constructed a `ClassifyResult` directly with that exact conflicting data and asserted the final
spec was castable.

It passed. It was committed. It was wrong.

`ClassifyResult._assemble` calls `_stone_shape()` on **every** attempt it makes, not only the
pure-default last resort — so the non-oval shape in the test's input collapsed `length_ratio` to
1.0 before the spec was ever assembled, and the conflicting-diameter scenario the test's own
docstring described never actually occurred. The first attempt converged normally, in one
ordinary repair pass, for a completely different reason than the test claimed. The assertion was
true; the test was not evidence of what it said it was evidence of.

This was caught by tracing the passing test by hand — printing the intermediate spec at each
attempt — not by any assertion failing. A green CI run would have shown nothing wrong. The tell
was self-suspicion at exactly the moment a green test made the strongest claim ("the fallback
chain handles real infeasibility") on the thinnest ground (one hand-built case, never inspected).

## Decision

**A new test that claims to exercise a specific code path is not trusted on green alone — trace
what it actually ran before committing it**, the same discipline this repo already applies to
gate rules (ADR-0005/6/7) and to the codebase in general (`CLAUDE.md`'s own Verify skill: "vet the
oracle... a test that's always green proves nothing"). The previously-established version of this
rule was about *inherited* tests and tests written against *the code's* assumptions. This extends
it one step further: a test written in the same sitting as the code, by the same reasoning, is
exactly as capable of encoding a shared blind spot as an inherited one — authorship does not
exempt a test from being traced, and "I just wrote it, I know what it does" is the same
overconfidence ADR-0006 already named in the code it tests.

**The concrete fix, and the reusable pattern:** when a scenario is genuinely hard to construct
through the real call path (here, because a normalisation step the test wanted to bypass runs on
every path, not a designated one), that is a sign to test the *mechanism* directly — inject the
failure (a fake `is_castable` forcing non-convergence, as the two sibling fallback-chain tests in
`tests/test_classify.py` do) — rather than fight to hand-build real-looking data that may not
reach the branch at all. A test of a safety net is honest when it forces the net to catch
something; it is not honest when it merely hopes the ball rolls that way.
