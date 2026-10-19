# 14. Look the number up, and when the lookup fails, record where you looked

- **Status:** Accepted
- **Date:** 2026-10-19 (lessons from 2026-08-06 and 2026-08-24)
- **Context ticket:** RNG-19 CP4 (halo plate), RNG-33 (stone cuts beyond round + oval).

## Context

Two tickets ran into the same weakness in how a number gets into this codebase.

**RNG-19 CP4: numbers set by eye get written up as principles.** The halo web
rule (the metal left between neighbouring accent seats) was relaxed after a
visual complaint. That change was later researched, and the research confirmed
it, but found two other problems. The *stated reason* for the relaxation was
wrong (the real defence is that the original measurement was taken at the
widest point of a tapered bore; see `specs/RNG-19.md`, "The web rule was relaxed
mid-checkpoint"). And a second number, the plate rim, had been eyeballed to
**half the trade figure**. Both had been written down in the voice of a
principle, which made them look like settled facts to the next reader.

**RNG-33: "we searched and found nothing" was written as "nothing exists".** A
first research pass over the cut geometry concluded "no published figure exists
anywhere" for every invented value in `docs/research/`. The user disputed that,
so a second pass ran. It found published figures for two of them in one search:
the emerald corner (US10448713B1 + AGS, giving **0.14W** where we had 0.15W) and
pear wing shape (straight wings are a *named defect*; correct wings are gently
convex). The rest (pear belly, marquise tip angle, tip radius, V-prong wrap) did
turn out to be unpublished, and the second pass checked the Stuller and Rio
Grande findings catalogues to say so. See `specs/RNG-33.md`, "Research pass
2026-08-24", and the two `docs/research/cut-outline-geometry-*.md` notes.

## Decision

1. **A dimension, tolerance or trade convention is looked up, not argued.** If
   a value is justified by reasoning instead of a citation, it is either sourced
   or marked in the code or research note as **our number, not a trade figure**
   (as `specs/RNG-25.md` does for the 0.8mm knife-edge apex). A value changed
   after a visual complaint gets the same treatment: the complaint is a reason
   to look, not a source.
2. **A failed lookup records where it looked.** "We searched X, Y and Z and
   found nothing" and "nothing exists" are different statements. Writing the
   second when you mean the first closes a question that is still open. The
   failed-lookup note names the sources tried, so a later pass can start where
   it stopped rather than repeating it, or can see at a glance which obvious
   source was never checked.

## Consequences

- `docs/research/` notes mark each value as *sourced*, *corrected* or
  *confirmed unsourced*, and say where the unsourced ones were looked for.
- An "invented" value is not a defect in itself. Some figures really are
  unpublished, and the geometry still needs a number. What's wrong is an
  invented value that reads as a sourced one.
