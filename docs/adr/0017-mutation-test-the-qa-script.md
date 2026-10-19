# 17. Mutation-test a QA script against the broken code before trusting it

- **Status:** Accepted
- **Date:** 2026-10-19 (lesson from 2026-09-16)
- **Context ticket:** RNG-29 (photo error message does not clear when a file is
  chosen); extends ADR-0010.

## Context

RNG-29 was a DOM-event bug: a status line ("Choose a JPEG or PNG photo first.")
outlived the condition it described. The house style for frontend tests is
Python source inspection (`tests/test_frontend_*.py`), and for an event bug
that can only show a listener is *wired*, never that it *fires*. The new tests
say so in their own docstring and are not the evidence.

The evidence was a real browser driving the real dev server (see ADR-0016). But
a QA script is a test like any other: if it has never been run against the
broken code, nothing shows it can fail. A script that passes against the fix is
compatible with a script that would pass against anything.

So the script itself was mutation-tested: `git stash push` the fix, rerun the
script, `git stash pop`. **Four target checks went red and three deliberate
controls stayed green.** Only then did its green run on the fixed code count as
evidence.

## Decision

**A QA script written to prove a fix is run once against the code *without* the
fix before its result on the fixed code is trusted.** Its target checks must go
red there, and it should carry at least one control check that stays green
either way, so a script that fails across the board (wrong URL, stale server)
is not mistaken for one that detects the bug.

This is ADR-0010's rule (trace what a passing test actually exercised) applied
to the scripts that sit outside the suite. They need it more, because nothing
else ever runs them.

## Consequences

- Stash-and-rerun is cheap for a single fix. For a multi-commit change, check
  out the pre-fix commit instead, as RNG-25's Verify did for its guard test.
- The browser QA harness is still uncommitted (it lives in scratchpads).
  Committing it is tracked in Orbit as RING-44, and this check belongs in
  that harness when it lands.
