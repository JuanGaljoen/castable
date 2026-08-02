# Probes

Developer tools that run the real app against real inputs. Not part of the
shipped application, never collected by `pytest`, and they cost money to run.

## Photo fidelity probe (RNG-22)

```bash
source .venv/bin/activate
python probes/fidelity_probe.py
```

Runs every photo in `probes/corpus/` through the same two calls the browser
makes — `POST /classify-ring`, then `POST /generate-ring` with the spec that
comes back — and prints one line per photo:

```
ok    solitaire-round.jpg     solitaire  watertight, no repair  4.2s
warn  halo-oval.jpg           solitaire  watertight, no repair  3.8s  <- expected halo, vision read solitaire
gap   side-stone.jpg          no photo in the corpus for this entry
ok    negative-puppies.jpg    correctly declined to detect a ring

3/4 generated · 2 pass · 0 fail · 1 archetype mismatch · 1 corpus gap
```

Generated geometry lands in `probes/output/` (gitignored) as `<slug>.stl` and
`<slug>.spec.json`, so a render can be opened beside the photo it came from.

### What it costs

**One live Anthropic vision call per photo** — about $0.003 each on the default
Haiku model, and roughly 4 seconds. The current corpus is five photos, so a full
run is a couple of cents and under a minute.

With no `ANTHROPIC_API_KEY` in the environment or a local `.env`, it prints a
skip message and exits 0. It never fails a run for want of a key, and the
offline test suite never invokes it.

### When to run it

Before and after anything that claims to move fidelity — geometry proportions
(RNG-19), shank profiles (RNG-25), vision estimates (RNG-26), viewer
presentation (RNG-27). Keep the `probes/output/` from the "before" run and
compare the two side by side.

The throwaway version of this script earned its keep the first time it ran: it
found that oval stones were being generated round (became RNG-23, shipped), that
WebP uploads were rejected before vision ever ran (RNG-28), and that a
castability failure we had assumed and written a ticket for did not exist at all
(RNG-20, deleted rather than built). None of that was visible to 3,400 passing
unit tests, because none of them ran a real photo through the real path.

### A caveat when comparing before and after

**Vision is not deterministic.** Across runs of the same corpus we have seen the same
photo classify as a ring once and not the next time (RNG-31), and produce a spec that
fails the casting gate one day and passes the next (RNG-32).

So a naive before/after — run it, change the geometry, run it again — compares two
different specs and cannot tell you whether your change helped. **Geometry is
deterministic given a spec; only the vision half wanders.**

For anything that changes geometry or presentation (RNG-19, RNG-25, RNG-27, RNG-33),
compare against a **saved spec** rather than re-classifying: keep the `<slug>.spec.json`
from the "before" run and POST it straight to `/generate-ring`. Re-run the full probe when
what you are measuring *is* the vision layer (RNG-26, RNG-31, RNG-32), and expect to run
it more than once.

### What it does and does not tell you

It reports what happened: which archetype vision picked, whether generation
succeeded, whether the mesh came out watertight and whether it needed repair.

It does **not** judge whether the model looks like the photo. That is deliberate
— human judgement of the output is the point. The probe's job is to make looking
cheap and repeatable, not to score it.

### The corpus

`probes/corpus/manifest.json` describes each photo: the archetype it should be
read as, or `expect_ring: false` for the negative case. **Adding a photo is a
manifest entry plus a file — no code change.**

An entry whose file is absent is reported as a `gap`, not a failure. That is how
`side-stone.jpg` is currently carried: the corpus declares the archetype should
be covered and the run says out loud that it is not. Drop a side-stone ring photo
in at that filename to close it.

Photos must be JPEG or PNG — `/classify-ring` sniffs magic bytes and accepts
nothing else until RNG-28 lands. `trilogy-oval.jpg` was converted from WebP for
exactly this reason.

### Verdicts

| Mark | Meaning | Affects exit code |
|---|---|---|
| `ok` | did what the corpus expects | — |
| `FAIL` | a ring photo failed to classify or generate, or a ring was detected in the negative photo | **yes, exit 1** |
| `warn` | generated fine, but vision read a different archetype than the corpus expects | no |
| `gap` | the manifest declares this entry but there is no photo for it | no |

Generation is the bar. An archetype mismatch is real signal worth a ticket, but
a genuinely ambiguous photo must not make the harness cry wolf, so it stays
amber.
