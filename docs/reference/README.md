# Reference sketches — what each archetype is supposed to look like

Design **targets**: trade sketches of the ring each archetype is trying to be.
One image per archetype, named for it, so "does this look right" has something
concrete to be judged against instead of resting on memory or taste.

| File | Archetype | Status |
|---|---|---|
| `halo.png` | halo | ✅ added 2026-08-06 |
| `solitaire.png` | solitaire | — wanted |
| `trilogy.png` | trilogy | — wanted |
| `side-stone.png` | side-stone (channel) | — wanted |

**Adding one is a file plus a table row.** No code change, same rule as the
fidelity corpus.

## Not the same thing as `probes/corpus/`

Easy to conflate, and the distinction is load-bearing:

| | `probes/corpus/` | here |
|---|---|---|
| What it is | photos of real rings | sketches of the ring we mean to build |
| Which end | **input** — fed to `/classify-ring` | **output** — what the STL should look like |
| Judged by | the harness, automatically | a human, at checkpoint boundaries |
| Failure means | vision or generation broke | the geometry is wrong in kind or proportion |

A corpus photo answers *"can we read this?"*. A sketch here answers *"is what we
built even the right object?"* — the question that found the channel setting was
halo geometry wearing a channel's name.

## Why sketches rather than photographs

**Semi-mounts.** Trade sketches show the mount with no stones set — empty
prongs, open seats. That is exactly what we render: metal only, no gemstones
(out of scope per RNG-27).

This matters more than it sounds. `../jewelry-design-principles.md` §"The
metal-only caveat" warns that a setting reads as the *negative* of its stone, so
a correct model can still look odd bare, and appearance judgements must allow
for it. A semi-mount sketch removes that excuse: it is bare metal too, and it
still reads unmistakably as jewelry. **If ours does not look like the sketch,
the difference is ours, not the missing stones.**

`halo.png` earned its place that way — it showed the halo body should be one
continuous plate with the accent seats bored through it, retained by small beads
between adjacent stones, where we had built a rim of collar tubes 0.7–0.8mm
thick around 1.2mm stones (RNG-19 CP4).

## How to read one

Sketches carry more than a silhouette. From `halo.png`:

- **the plan view** gives proportion — halo width against the centre stone, and
  how much metal sits between adjacent accents;
- **the front elevation** gives the understructure — the gallery reads as an
  open arched basket, not a solid hub;
- **the detail callout** names the retention explicitly ("SMALL PRONG
  SETTINGS"), which is the field most easily got wrong from a photo, because
  retention is what distinguishes channel from pavé from a halo.

Note also what a sketch shows that is **out of scope**: `halo.png` has pavé set
down the shank, which our archetype union cannot express at all (→ RNG-24). Read
the sketches for the archetype in hand, and file the rest rather than smuggling
it in.
