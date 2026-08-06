# Jewelry design principles (proportions + finishing)

Real-world conventions for the four archetypes we build, gathered for RNG-19 so
proportion choices are defensible numbers rather than eyeballed ones. Absolute
millimetres where the trade uses them, ratios where it doesn't.

Sources are listed at the bottom. These are trade conventions, not physical laws —
they describe what reads as jewelry, and deliberate departures are fine when named.

## Shank (band)

| Property | Convention | Ours today |
|---|---|---|
| Width | 1.5–3mm, most engagement rings ~2.5mm | `band_width` 2.0 ✓ |
| Width at narrowest | keep ≥ 2mm for stability | not enforced |
| Taper | width narrows from head toward the back | `SHANK_TAPER` 1.7 |
| Thickness | stays roughly constant around the ring | **also × 1.7** ✗ |
| Cathedral rise | 2.0–4.5mm above the shank | RNG-25 |

**The finding that matters.** `_band_section` applies `taper` to *both* axes:

```python
th = _lerp(c["bt"], c["bt"] * c["taper"], t)   # thickness — should stay ~flat
w  = _lerp(c["bw"], c["bw"] * c["taper"], t)   # width — correctly tapers
```

Real shanks taper in **width**; thickness stays near-constant so the ring keeps a
consistent feel on the finger. Tapering both by 1.7 makes the band 3.4mm wide *and*
3.06mm thick at the head — a swollen tube rather than a shank rising to a head.
This is the single biggest reason the band reads as parametric.

## Prong / claw

| Property | Convention | Ours today |
|---|---|---|
| Diameter | 0.75–1.25mm; 1×1mm common | `wire_r` 0.5 → **1.0mm** ✓ |
| Profile | rounded, U-shaped outer face | sphere-and-cone chain ✗ |
| Length | 2–3mm | derived from `claw_rise` |
| Tip height | finish at roughly table level | `claw_rise` |
| Taper | tapers toward the tip | **constant radius** ✗ |
| Casting floor | ~1mm is near the practical wax-cast limit | `MIN_PRONG_TIP` 0.7mm |

**Our claw diameter is already right.** The defect is shape, not size: constant
`wire_r` with a `Sphere` at every node reads as bent wire with ball joints. The fix
is a continuous taper to a domed tip, not a thicker prong. Note the trade's caution
that ~1mm is close to the wax-casting limit — our 0.7mm floor is aggressive, so
tapering *toward* the tip must not go below it.

## Halo

| Property | Convention |
|---|---|
| Accent diameter | micro 1.0–1.25mm · **classic ~1.5mm** · large 1.75–2.0mm (up to 3mm) |
| Spacing | evenly spaced, matched, level, each supported by enough metal |
| Gap to centre | usually none; deliberate negative space is a named style choice |
| Halo body | **one continuous plate**, seats bored through it; crisp outer rim |
| Retention | **small beads between adjacent stones**, not a few large shared claws |
| Understructure | an **open arched basket**, not a solid hub |

**Metal between adjacent stones is PAPER-THIN, and the 0.8mm floor does not
apply to it** (researched 2026-08-06, after the RNG-19 CP4 rule was changed on a
visual judgement and needed checking):

| Quantity | Trade figure |
|---|---|
| gap between neighbouring stone girdles | **enough to slide a piece of paper** (~0.1mm) |
| metal beyond the outermost stone (the rim / bright cut) | **>= 0.5mm each side** |
| seat bottom | drilled through at ~0.5mm; metal remains beneath |

The casting floors are **classed**, which is the part we had wrong: *"structural
and external walls ... 0.8mm, with smaller elements such as claws or small
setting bezels ... 0.5mm"*, and micro-pave features down to 0.35mm. **The metal
between two stone seats is a setting element, not a structural wall**, so
applying the 0.8mm structural floor to it was a category error — the same shape
of mistake as using halo geometry for a channel setting. Our rule now leaves
0.15mm between stones, which matches the trade.

**The body is a plate, not a ring of collars** (`reference/halo.png`, 2026-08-06).
Ours builds N `accent_seat` torus collars that happen to overlap into a scalloped
rim — on the corpus halo that is a 0.7–0.8mm tube around a 1.2mm stone, so the
metal is two thirds the stone's own diameter and reads as lumpy tubing.
`collar_tr = max(MIN_WALL/2, 0.35)` is pinned at the casting floor, so on small
accents it *cannot* get finer by tuning. The fix is the RNG-19 CP3 move applied
again: make the plate solid and **cut the wells out of it**, so the metal between
stones is what the cuts leave rather than the sum of fat tubes (→ RNG-19 CP4).

Accents are specified in **absolute mm**, not as a ratio of the centre stone — a
1.5mm accent is 1.5mm whether the centre is 1ct or 3ct. Worth knowing before
anyone "improves" the halo by scaling accents with the centre.

## Trilogy (three-stone)

| Property | Convention |
|---|---|
| Classic ratio | **1 : 0.5 : 1** by carat — sides half the centre's weight |
| Alternatives | 1 : 0.75 : 1 (heavier) or sides ⅓ the centre |
| Combined sides | ¼ to ½ the centre's carat weight |
| Spacing | sides sit close to the centre; the three read as one line |

**Carat is volume, so a 0.5 carat ratio is ~0.79 in diameter** (0.5^⅓), not 0.5.
For an 8mm centre that's a ~6.3mm side stone.

**Where ours goes wrong is spacing, not size.** `side_stone_gap: 2.0mm` pushes the
angular offset to 51° per side (see `specs/RNG-19.md`), splaying the sides toward
the sides of the finger. The three stones should read as one continuous line, which
means a gap in the tenths of a millimetre and near-coplanar tables — not each stone
rotated to face outward.

## Channel / side-stone

This is the one where our model is not merely unrefined but **wrong in kind**:

- Stones sit in a **groove cut into the band**, held by a metal wall on each side.
  **No prongs and no per-stone collar at all** — that is the definition of channel.
- The setter cuts seats into the **inner faces of both walls**, slightly below each
  stone's girdle, so the girdle rests in the groove and the **crown stays visible
  above the metal**.
- Typical undercut ~0.25mm deep; girdle penetration into the channel ~0.2mm.
- Channel demands dimensional accuracy: uniform wall pressure along every girdle.

Ours places an `accent_seat` at each stone — a `Torus` collar deliberately left
proud of the band (`ACCENT_EMBED = 0.1`, commented "a visible bead"). That is
correct halo geometry reused where its premise doesn't hold, producing a row of
raised donuts instead of stones recessed between two rails.

## The metal-only caveat

We never render gemstones (out of scope per RNG-27), so every model is the metal
alone. Any setting therefore reads as the *negative* of the stone: a channel row is
a groove with seat recesses, a halo is a ring of collars with empty wells. Judging
"does this look like jewelry" has to account for the missing stones — the metal can
be correct while the render still looks odd.

**Do not over-claim this caveat (2026-08-06).** It excuses a *correct* model
looking odd; it does not excuse a wrong one. `reference/halo.png` is a trade
semi-mount — bare metal, empty prongs, no stones set, exactly our situation —
and it reads unmistakably as jewelry. So "you cannot judge it without stones"
was doing more work than it deserved: it was part of the reasoning that deferred
the seat/collar blends out of RNG-19, and a single reference sketch overturned
it. **Where a semi-mount sketch exists, compare against it and the caveat does
not apply.** See `reference/README.md`.

## Sources

- [Robinson's Jewelers — center-to-side ratio for three-stone rings](https://robinsonsjewelers.com/blogs/news/for-a-3-stone-engagement-ring-what-is-the-ratio-of-center-stone-to-side-stones)
- [Brian Gavin Diamonds — ratio of center to accent diamonds](https://www.briangavindiamonds.com/blogs/news/what-ratio-of-center-stone-to-accent-diamonds-is-best-for-a-three-stone-ring)
- [Victor Canera — three-stone design guide](https://victorcanera.com/us/blog/three-stone-engagement-ring-design-advice)
- [Ganoksin Orchid — CAD manufacturing guidelines for claw prongs](https://orchid.ganoksin.com/t/recommendation-cad-manufacturing-guidelines-for-claw-prongs/57880)
- [Ganoksin Orchid — prong diameter guide](https://orchid.ganoksin.com/t/prong-diameter-guide/28578)
- [PriceScope — minimum prong size that can be wax cast](https://www.pricescope.com/community/threads/what-is-the-minimum-size-prongs-that-can-be-wax-cast.211740/)
- [Engagestudio — halo accent stone sizes](https://www.engagestudio.com/pebble/halo-engagement-ring/)
- [Blue Nile — halo settings](https://www.bluenile.com/engagement-rings/styles/halo)
- [Ganoksin — step by step guide to single row pave settings](https://www.ganoksin.com/article/step-step-guide-single-row-pave-settings/) (paper-thin girdle spacing; 0.5mm bright-cut allowance)
- [Cooksongold — top tips for the perfect CAD design](https://www.cooksongold.com/blog/learn/top-tips-for-the-perfect-cad-design/) (0.8mm structural vs 0.5mm setting elements)
- [Stuller — pave setting](https://www.stuller.com/articles/view/pave-setting/)
- [Stuller — techniques for channel setting](https://www.stuller.com/articles/view/techniques-for-channel-setting/)
- [FlashForge — complete channel setting guide](https://enterprise.flashforge.com/blogs/blog-1/what-is-channel-setting-complete-jewelry-stone-setting-guide)
- [Serendipity Diamonds — shanks and shoulders](https://www.serendipitydiamonds.com/blog/engagement-rings-from-the-shank-up-to-the-shoulders/)
- [Emerson Fine Jewelry — low-profile vs cathedral](https://www.emersonfinejewelry.com/blogs/blog/redlands-custom-engagement-rings-sizing-comfort-low-profile-vs-cathedral-explained)
