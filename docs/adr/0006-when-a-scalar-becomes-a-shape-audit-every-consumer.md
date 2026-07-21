# 6. When a scalar becomes a shape, audit every consumer — the abstraction only protects the ones that adopt it

- **Status:** Accepted
- **Date:** 2026-07-21
- **Context ticket:** RNG-23 (oval centre stone)

## Context

RNG-23 replaced the `stone_r` scalar with a `StoneOutline`, on the reasoning that the girdle's
shape should live in one place instead of being branched on in six. The design classified
consumers into two kinds and served each with the narrowest thing it needed:

- **curve-walkers** (`seat`, `bezel`, `prong_setting`, `halo`) get the path and frames;
- **width-consumers** (`trilogy` placement, the overcrowding checks) get a half-width.

That classification was right. The mistake was assuming that *making* the classification was the
same as *applying* it everywhere. Three separate consumers kept measuring with the short axis
after the stone stopped being round, and each was found by a different mechanism:

1. **`trilogy` placement + overcrowding** — found during CP2, by working through the design.
   Side stones flank along the band, the same axis an N-S oval is longest on.
2. **`halo_overcrowding`** — found only by running a **real photo** end to end. An oval halo
   classified correctly and was then rejected, because the accent arc was computed from a circle
   of the short axis while CP3 had made the ring an ellipse. The gate was refusing a ring the
   geometry could build. No unit test caught it: every test that could have was written against
   the same wrong mental model as the code.
3. **`stone_exceeds_bore`** — found by deliberately auditing for the pattern after (2), rather
   than by any test or user report. A 10mm stone at `length_ratio` 2.5 is 25mm long across a
   16.5mm finger bore and passed the gate.

The through-line: an abstraction constrains the code that *adopts* it and does nothing for the
code that doesn't. Every site still holding the old scalar is silently exempt, and the compiler
cannot help because the scalar is still a perfectly valid float.

## Decision

**When a scalar is generalised into a shape, enumerate its consumers exhaustively and decide for
each one, in writing, before the change is called done.** `grep` for the old name and classify
every hit; do not stop at the sites the feature obviously touches. A consumer that legitimately
still wants the scalar (peg radius, hub radius — scale values, not girdle-following ones) should
be recorded as such, so the next reader knows it was considered rather than missed.

**Corollary — validation gates need auditing more urgently than builders.** A builder that
ignores the new shape produces visibly wrong geometry. A *gate* that ignores it silently rejects
valid designs (`halo_overcrowding`) or silently admits invalid ones (`stone_exceeds_bore`).
Neither shows up as a failing test, because gates are usually tested with the same assumptions
that produced them.

## Consequences

- Reviewing RNG-23's own generalisation surfaced no further short-axis consumers:
  `side_stone` accents run along the shank, not around the stone, and the peg/hub radii are
  deliberately scale-derived.
- **Run the real path before calling shape work done.** The halo bug survived a 3404-test green
  suite and was exposed by one photo. This is the same lesson as `docs/adr/0004`
  ("verify against the real API once") arriving from a different direction: stubs and unit tests
  inherit the author's assumptions, and only real input carries assumptions of its own.
- Future shape families (emerald, pear, marquise) extend `StoneOutline` rather than adding
  fields, so the consumer audit is a one-time cost already paid — provided new gates are written
  against the outline and not against `stone_diameter`.
