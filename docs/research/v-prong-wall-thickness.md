# V-prong (V-tip) wall thickness

**Status: ANALOGUE-ONLY.** No source found — trade catalogue, casting-house spec, or
CAD guide — publishes a wall-thickness figure for a V-prong/V-tip specifically. What
exists is two adjacent, better-documented figures that bound the question: (a)
hand-fabricated **bezel wire gauge**, and (b) **generic minimum-wall/prong specs**
from lost-wax casting and casting-bureau design guides. Both are reported below,
clearly labelled as analogues, not as V-tip figures.

This is a second pass on the same question a prior pass already researched (Stuller,
Rio Grande, Ganoksin — "no published dimension exists" for V-prong wrap/reach). This
pass attacked five different angles per the task brief; results below.

## What was checked

1. **Bezel wall thickness** (closest structural analogue — a V-cup is a partial
   bezel). Found figures, see below.
2. **Sheet gauge convention.** Found — bezel work is conventionally specified in B&S
   gauge, not mm, and the trade gives a real range.
3. **Stuller/Rio Grande V-tip catalogue SKUs.** Searched Stuller's finding catalogue
   (`stuller.com/browse/findings/settings`, princess/square V-prong peg settings,
   V-End filter category) — listings identify V-prong heads by stone size and metal
   karat/finesse, **not** by wall thickness or gauge. No dimensional spec surfaced.
   This confirms, from a different angle, the prior pass's finding: the catalogues do
   not publish this number for a finished V-tip finding.
4. **Casting/print bureau minimum-wall specs.** Found — Materialise and Shapeways
   both publish numeric design-guide minimums for lost-wax-cast gold/silver. General,
   not V-tip-specific, but primary and numeric.
5. **Jewelry CAD guidance** (Matrix/RhinoGold/GemVision tutorials). Searched;
   nothing beyond generic "avoid walls under 0.8mm" advice repeated across CAD
   blogs (Honho, UrgentCAD) with no attribution to a spec document. Not treated as a
   source below — it just restates angle 4's figures without adding a number.

## The numbers

**Bezel wire gauge (hand-fabricated bezels, closest structural analogue):**

| Gauge | mm | Use | Source |
|---|---|---|---|
| 30g | 0.25mm | thinnest bezel wire, "easier to push over... by hand" | [Metalsmith Society, Guide to Ordering Metal](https://metalsmithsociety.com/a/blog/metalsmith-societys-guide-to-ordering-metal-for-jewelry-making) |
| 28g | ~0.32mm | recommended for hand-set bezels, beginner-friendly | [Metalsmith Society](https://metalsmithsociety.com/a/blog/metalsmith-societys-guide-to-ordering-metal-for-jewelry-making); corroborated by [Rock Seeker, backplate gauge guide](https://rockseeker.com/backplate-for-bezel-set-ring/) ("28 gauge bezel wire strikes the perfect balance") |
| 24g | 0.51mm | bezel wire, heavier stones | [Metalsmith Society](https://metalsmithsociety.com/a/blog/metalsmith-societys-guide-to-ordering-metal-for-jewelry-making) |
| 20–22g | 0.81–0.64mm | rigid setting for a large (22×30mm) cabochon; explicitly called "strong rigid" by a practicing bench jeweler, i.e. towards the heavy/structural end | forum reply "coralnut1" on [Ganoksin Orchid: Thickness of bezels](https://orchid.ganoksin.com/t/thickness-of-bezels/18542) — **forum post, not a spec document** |
| up to 1.2mm | — | one jeweler reports hammer-setting sterling this thick | forum reply "brian" on the same [Ganoksin thread](https://orchid.ganoksin.com/t/thickness-of-bezels/18542) — anecdotal outlier |

Note on how a hand-fabricated bezel is built: it is **one continuous strip of metal**
that stands proud of the seat and is then burnished/pushed over the stone — the "wall"
and the "inward lip" are the same piece of metal at the same gauge, not two stacked
layers. None of the sources above describes a bezel as wall-thickness-plus-a-separate-
lip-thickness. This is a structural observation about how the analogue is built, not a
sourced claim about V-tips — flagging it because it bears directly on how our 0.65 +
0.30 figure should be read (see verdict).

**Generic minimum-wall / prong specs (primary, from casting/print bureaus, not
V-tip- or bezel-specific):**

| Feature | Min | Source |
|---|---|---|
| General wall thickness, gold | 0.8mm | [Materialise, Design Guidelines for Gold](https://www.materialise.com/en/academy/industrial/design-am/gold) |
| Ring band wall thickness, gold | 1.0mm | same |
| Prong/rod diameter, gold | 0.8mm min | same |
| Fine engraved/embossed detail wall, gold | 0.35mm (at ≤1:1 depth:width) | same — **not a bezel or prong figure, a surface-detail one** |
| General wall thickness, silver | 0.6mm (gloss) / 0.8mm (high-gloss) | [Materialise, Design Guidelines for Silver](https://www.materialise.com/en/academy/industrial/design-am/silver) |
| Ring band wall thickness, silver | 1.0mm | same |
| Prong/rod diameter, silver | 0.8mm min | same |
| Minimum clearance between adjacent parts | 0.3mm | same |
| Absolute min wall, precious metal | 0.8mm | [Shapeways forum citing internal spec](https://www.shapeways.com/forum/t/cast-metal-recommended-thickness-for-flat-surfaces.98745/) |
| Prong/rod diameter (mesh-like structural features) | 0.8mm min | same Shapeways source |

## Agrees / contradicts — our 0.65mm outer + 0.30mm lip = 0.95mm

**No source states 0.95mm, or any V-tip total, directly — so there is no strict
agree/contradict against a named figure.** But weighed against the analogues:

- Our **outer wall alone (0.65mm)** already sits above the bezel trade's commonly
  recommended range for typical stones (28g/0.32mm, up to 24g/0.51mm) and close to
  the *heavy-duty, large-cabochon* end (20–22g, 0.81–0.64mm) — the gauge bench
  jewelers use for oversized, hand-hammered settings, not typical faceted diamonds.
- Our **total of 0.95mm** exceeds every bezel-wire figure found, including the
  heaviest anecdotal one from a working jeweler for a large rigid cabochon bezel
  (20ga / 0.81mm) and is close to the one outlier report of 1.2mm hammer-set sterling.
- The casting-bureau generic minimums (0.8mm wall, 0.8mm prong) are satisfied by our
  outer wall alone (0.65mm is actually *below* their generic 0.8mm floor, though our
  project's own stated floor is also 0.80mm — worth checking that 0.65mm doesn't
  itself violate the project's minimum-wall rule independent of this question).
- Given the fabricated-bezel construction pattern (single gauge, folded, not two
  stacked layers), **treating "outer wall" and "inward lip" as separately-sized,
  additive layers has no analogue in the sources reviewed.** That additive
  construction — 0.65 + 0.30 — is a plausible candidate for why it reads thicker than
  photographed V-tips: the trade reference photographs are (per this analogue) a
  single gauge of metal folded over, typically 0.32–0.51mm for typical stone sizes,
  not two stacked thicknesses summing near 1mm.

**Verdict: the user's visual judgment is corroborated by the analogue evidence.**
0.95mm total is thicker than any bezel-wall figure found for anything but oversized,
hand-hammered cabochon settings, and the additive wall+lip construction itself looks
non-standard against how a bezel/V-cup is normally described as being built (one
strip, one gauge, folded).

## Does the inward lip have its own conventional figure?

**Not found.** None of the sources — bezel-gauge trade guidance, casting-bureau
specs, or CAD tutorials — describes a retaining lip/bezel-fold as a dimension
distinct from the wall gauge itself. The trade treats "how far it folds over" (a
reach/overlap question) and "how thick the metal is" (the gauge question) as the two
relevant numbers, not "wall thickness" and "lip thickness" as two separate radial
figures. (Wrap distance/reach was the subject of the prior research pass and was
also not found published.)

## Confidence

**ANALOGUE-ONLY / thin-to-moderate.** The bezel-gauge figures are the closest
functional analogue and reasonably well corroborated across three independent bench-
jewelry sources (Metalsmith Society, Rock Seeker, Ganoksin forum), but bezel ≠ V-tip
and none is a controlled spec document — the Ganoksin numbers in particular are
anecdotal forum replies and should be weighted accordingly. The casting-bureau
figures (Materialise, Shapeways) are genuine primary spec documents but are generic
minimum-wall/prong numbers, not shaped-feature guidance, so they bound the *floor*
without addressing the *typical* V-tip thickness at all. Trust the bezel-gauge range
(0.25–0.81mm, centred around 0.32–0.51mm for ordinary stone sizes) as the best
available proxy for "what a V-tip wall reads as" in a photograph; do not trust it as
a substitute for an actual V-tip figure, which remains unpublished after two research
passes from eight distinct angles.
