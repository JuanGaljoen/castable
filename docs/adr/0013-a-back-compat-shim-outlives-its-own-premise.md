# 13. A back-compat shim outlives its own premise

- **Status:** Accepted
- **Date:** 2026-09-12
- **Context ticket:** RNG-24 (composable features) CP1 -> CP3.

## Context

CP1 collapsed RingSpec's four-way archetype union into one model carrying
optional `halo`/`trilogy`/`side_stone` groups. The stored `archetype`
discriminator went away with it, but several callers still keyed on one:
`classify.py`'s JSON contract, its tests, and `probes/fidelity_probe.py`'s
corpus mismatch check all read `spec["archetype"]`.

Rather than migrate them in CP1, `coherence.make_coherent` re-attached the
key on its way out, derived from a new read-only property:

```python
working = {**working, "archetype": model.archetype}
```

The property returns the single active feature's name by precedence
(`halo` > `trilogy` > `side_stone`), or `"solitaire"` when none is set. CP1
documented the limit in the model's own docstring — *"meaningful only while
at most one feature is present"* — and in its checkpoint notes, deferring the
caller migration to CP3.

That caveat was true when written. CP1 and CP2 had no way to produce a
multi-feature spec: the contract allowed one, but nothing emitted one. **CP3
is the checkpoint that makes multi-feature specs real**, and the shim was
carried into it unchanged.

The first real photo uploaded after CP3 landed returned a 500. Vision read
`probes/corpus/halo-round.png` correctly and in detail — a halo with
pave-set shoulders — so `_assemble` produced a spec carrying BOTH the `halo`
and `side_stone` groups. Then:

1. `make_coherent` dumped it and stamped `archetype: "halo"` on the result,
   because halo wins the precedence.
2. `_coherent_spec` passed that dict straight back into `validate_spec`.
3. `validate_spec` saw an `archetype` key, took the **legacy translation
   path**, and applied the rule that path exists to enforce: the named
   archetype's group must be present and every OTHER feature group absent.
4. `side_stone` was present. `archetype_group_conflict`. 500.

**The spec poisoned itself passing back through its own validator.** Nothing
external was wrong: vision was right, the contract could hold the answer, the
geometry could build it. The only thing that rejected it was a label the app
had stamped on it one function earlier.

No test caught it. Every fixture in the suite had at most ONE feature — the
tests were written against the shape that existed when they were written, not
against the shape the ticket was creating. The suite was fully green.

## Decision

The shim is removed. `make_coherent` returns the dumped spec unchanged, with
no `archetype` key. `probes/fidelity_probe.py` derives its own single-name
label from the groups actually present (`archetype_label`), which reads
identically to before for a one-feature ring (`"halo"`) and honestly for a
combined one (`"halo+side_stone"`).

A regression test round-trips a genuinely multi-feature `ClassifyResult`
through `to_json()`, which is the exact path that 500'd.

## Consequences

**A shim's expiry date is a checkpoint, not a date.** This one was correct
on the day it was written and wrong the moment a later checkpoint delivered
the capability it could not represent — and that checkpoint was named, in the
same ticket, in the note deferring the migration. The comment said "revisit
in CP3"; CP3 arrived and nobody revisited, because the shim was still passing
its tests.

**When deferring a migration, write the test that will fail when the deferral
expires.** A comment describing the limit is not enforcement — it is a note
to a reader who may never come. Had CP1 added a single test round-tripping a
two-feature spec, it would have been red from the moment CP3 made two
features reachable, which is precisely when someone needed to be told.

**A green suite proves the code matches the tests, not that it matches the
ticket.** Every fixture here had one feature because every fixture predated
the feature set. This is the same failure ADR-0010 records from the other
direction (a test written in the same sitting as its code, passing while
testing nothing) and the same lesson RNG-22/RNG-23 keep relearning: the real
path found in one upload what 3900 tests could not.

**Accepting the derived label as an output was the original mistake.** A
value that is only meaningful under a condition the codebase is actively
removing should not be persisted into a payload other code consumes. If a
caller needs a single name for a thing that no longer has one, the caller
derives it — where the derivation's assumptions are visible — rather than
receiving it from a layer that cannot know whether they hold.
