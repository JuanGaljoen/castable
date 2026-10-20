# 15. Give the sample size when retiring work on empirical grounds

- **Status:** Accepted
- **Date:** 2026-10-19 (lesson from 2026-08-01)
- **Context ticket:** RNG-20 (deleted), RNG-22 (photo fidelity probe), RNG-32.

## Context

RNG-20, "vision spec castable by construction", was deleted on 2026-07-20. Its
premise looked disproved: real ring photos run end to end through
`/classify-ring` -> `/generate-ring` came back **3/3 raw watertight, zero
repairs**, so the ticket appeared to be solving a hypothetical.

On 2026-08-01 the first run of the RNG-22 probe, with more photos, brought the
premise straight back. `halo-round.png` produced `stone_height: 5.2` against
`setting_height: 3.0`, a stone taller than the head that holds it, and the
casting gate rejected it (`stone_exceeds_head`). That was filed as RNG-32
(`specs/RNG-22.md`, finding 2). The same photo then passed the gate the next day,
because vision is not deterministic, so the failure was intermittent as well.

Three samples had looked like evidence and were an anecdote. The deletion note
said *that* the premise was disproved, not *on how much*, so nothing in it
invited anyone to doubt it.

## Decision

**When a ticket is deleted, closed or descoped on empirical grounds, the note
says how many samples the evidence rests on** (e.g. "3/3 corpus photos clean"),
and, where the measured layer is non-deterministic, how many runs.

The sample size goes in the obituary itself, beside the conclusion, so a later
reader can weigh it without digging up the run.

## Consequences

- A small sample is still a valid reason to deprioritise. The rule is only that
  the size travels with the conclusion.
- For the vision layer specifically, one run per photo is not a sample of that
  photo. `probes/README.md` already says to run the probe more than once when
  the thing being measured is vision.
