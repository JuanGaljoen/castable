# Plan-view outline geometry: cushion and emerald cuts

**Question:** does published/measurable material constrain our plan-view outline
parameters — cushion's superellipse exponent `n = 3.0`, emerald's corner
truncation `0.15 × width`?

**Context / correction to a prior pass:** an earlier research attempt concluded
"no published figure exists anywhere" for this geometry and the values were
invented. That conclusion was **wrong for the emerald corner** — a granted US
utility patent explicitly defines and numerically bounds exactly the quantity we
need, and a second, independent AGS source resolves the one ambiguity that
patent left open (see Q2). It was **right for the cushion** — despite a real
search effort across faceting literature, GIA, IGS, and patents, no source gives
a corner radius, bulge/sagitta, or outline-fitting figure for a cushion. So:
partially lazy, partially correct. Both hold at once, for different questions.

---

## Question 1 — CUSHION: corner radius / side convexity

**Verdict: thin. No source gives a number for corner radius, side bulge, or an
equivalent that a superellipse exponent could be fit to.** `n = 3.0` remains an
eyeballed value with no citable anchor.

What the sources *do* establish, short of a number:

- **GIA's own description is qualitative only**: a cushion is "a square or
  rectangular shape with rounded corners," and GIA distinguishes **Cushion
  Brilliant** (round-brilliant-derived facet pattern) from **Cushion Modified
  Brilliant** (extra pavilion facet row, "crushed ice" look) — a facet-pattern
  distinction, not an outline-geometry one, and it carries no curvature figure.
  [GIA 4Cs, "Cushion Cut Diamond: An Old and New Classic"](https://4cs.gia.edu/en-us/blog/cushion-cut-diamond-old-new-classic/)
- **A real, granted construction exists that is NOT a superellipse.** US Patent
  Application US20150020544A1 / EP2826392A1 ("Cushion shaped hearts and arrows
  gemstone and method") defines the cushion outline as **four long sides of
  constant radius (near-straight, described as "a slight curvature but
  otherwise substantially straight") joined by four corner arcs of equal
  radius** — i.e. a rounded-rectangle / stadium-style construction with two
  distinct radii (a large one for the sides, a small one for the corners), not
  a single continuously-varying-curvature exponent. No numeric radius value is
  given for either radius, in fraction-of-width or absolute terms — the patent
  claims describe the *topology* of the curve, not its magnitude.
  [US20150020544A1, Google Patents](https://patents.google.com/patent/US20150020544A1/en)
  This is a genuinely useful finding for us independent of the missing number:
  it confirms the trade's own mental model of a cushion is two-radius
  (straight-ish sides + rounded corner), not the smooth all-over curvature a
  superellipse produces. A superellipse is a reasonable *approximation* of that
  two-radius curve, but nothing in the sources validates `n = 3.0` as the
  approximation's right exponent over, say, `n = 2.5` or `n = 4`.
- **Old mine / antique vs. modern cushion differ in outline, confirmed only
  qualitatively.** Multiple trade sources agree antique (old mine) cushions
  read "squarer" / "more irregular," refined over time toward the modern
  cushion's proportions — but none quantify it (no radius, no exponent, no
  angle).
  [Brilliance, "Cushion vs. Old Mine Cut"](https://blog.brilliance.com/education/cushion-vs-old-mine-cut);
  [GOODSTONE, "Elongated Old Mine Cuts vs. Standard Old Mine Cuts"](https://www.goodstoneinc.com/blogs/news/elongated-old-mine-cuts-vs-standard-old-mine-cuts)
- **Faceting design literature** (IGS "Faceting Made Easy" series, USFG
  diagrams) documents cushion faceting *patterns* (crown/pavilion facet
  counts and angles) exhaustively but the outline itself is a given input to
  those designs, not a derived/published curve.
  [IGS, "Faceting Made Easy, Part 6"](https://www.gemsociety.org/article/faceting-made-easy-part-6-gemstone-design/)
- **CAD faceting tools (GemCad, DiamCalc)** parameterize cushion designs by
  crown/pavilion angle, depth, and facet count — not by an outline-curve
  formula. No outline math surfaced.
  [OctoNus DiamCalc](https://www.octonus.com/3dcalc-software/diamcalc)
- **GIA does not grade fancy-shape cut** (confirmed): GIA's fancy-shape cut
  research (Fall 2024 *Gems & Gemology*) covers **oval, pear, and marquise**
  outline/appeal research specifically — not cushion, not emerald. So even
  GIA's most recent outline-appeal work does not reach these two shapes.
  [GIA, "Observations of Oval-, Pear-, and Marquise-Shaped Diamonds," Fall 2024 G&G](https://www.gia.edu/gems-gemology/fall-2024-fancy-shaped-diamonds)

**What this means for `n = 3.0`:** it agrees with nothing and contradicts
nothing, because no source states a comparable number. It should be labeled
in-code/spec as an aesthetic choice, not a cited constant. If a future pass
wants a defensible value, the two-radius (side-radius + corner-radius)
construction from US20150020544A1 is the more literature-backed shape family
to fit against — but even that needs someone to digitize an actual cushion
girdle (e.g. from a GIA plotting diagram or a manufacturer's calibrated
outline drawing) to get numbers, which this pass did not locate.

---

## Question 2 — EMERALD: corner truncation

**Verdict: settled, and it contradicts our current value.** A granted US
patent explicitly defines and numerically bounds the exact plan-view quantity
we model, and a second, independent primary source resolves the one ambiguity
the patent's text left open — by showing, not describing, exactly what the
quantity spans. Our `0.15 × width` sits **above** the resolved range.

### The primary source

**US Patent 10,448,713 B1, "Emerald-cut diamond"** (Google Patents' and
FreePatentsOnline's machine-readable renderings used; USPTO's own PDF is a
scanned/CCITT-encoded image that could not be OCR'd in this pass, so those two
mirrors are the actual sources read, not courtesy secondary sources — the
patent number is the citable object):
[US10448713B1, Google Patents](https://patents.google.com/patent/US10448713B1/en) ·
[US10448713, FreePatentsOnline](https://www.freepatentsonline.com/10448713.html)

It explicitly defines a **corner ratio (CR)**:

> "a variable corner ratio CR, i.e., the ratio of the corner width to the
> width W, as measured along the width W... high corner ratios CR produce a
> more octagonal stone, whereas a low CR is more square or rectangular."

Specified range: **CR = 13.5% to 14.5% of W, preferred ≈ 14.0% (±0.25)** —
measured at the girdle. Worked examples in the patent's own grade-map tables
(figures 8A, 9A, 13) all use **CR = 0.14** at L/W = 1.35, table = 55%.
Length-to-width ratio claimed: **1.325–1.425** (independent claim 1); a
dependent claim range of **1.35–1.40 (±0.025)** appears in the specification.

### The ambiguity — resolved

The patent's own prose never spells out whether "corner width" is one
corner's truncation along W, or the combined span of both corners at one end
(these differ by exactly 2×: one reading implies our `0.15W` needs to drop to
~0.14, the other implies it needs to drop to ~0.07). Chasing the patent's own
figures/claims further did not resolve it — Claim 1 mentions "corners" with no
numeric CR at all (CR lives only in the description as a preferred
embodiment, not a claim limitation), and the scanned drawings could not be
rendered in this environment (no PDF-page-rendering tool available; both the
raw USPTO PDF and the Google Patents-hosted PDF are CCITT-encoded scans with
no extractable text layer over the figures).

**A second, independent source settled it instead.** The American Gem
Society's own reference document, "Emerald Cut Geometry — Parameters,
Assumptions and Naming Conventions" (AGS members' technical library, dated
2006), gives a **labeled diagram**, not prose, defining exactly this
quantity — this is the primary source that closes the gap, and it is fully
independent of the patent (different publisher, different medium):
[AGS, "Emerald Cut Geometry — Parameters, Assumptions and Naming Conventions" (PDF)](https://cdn.ymaws.com/members.americangemsociety.org/resource/collection/5BCC3840-BEFB-48B7-A29D-61E4068B85F6/Emerald_Cut_parameters_assumptions_naming_conv.pdf)

The diagram shows a green dimension bracket labeled "CR" running from the
diamond's **top-right corner vertex inward to where the flat top (length)
edge begins**, alongside a separate brown bracket spanning the full width W
down the right side. The caption reads, verbatim: **"Corner Ratio (CR) is
equal to CR/W, where W is the width."** The bracket spans **one corner only**
— it does not run corner-to-corner across the end of the stone. AGS's own
"Emerald Cut Shape" section confirms CR is one of exactly two parameters
("Length-to-Width Ratio" and "Corner Ratio Percentage") that determine the
whole outline, i.e. a single scalar per stone, consistent with "one corner's
truncation" (a combined corner-to-corner span would still be a single scalar
too, but the diagram itself removes the need to infer from that).

**This settles reading (a): CR is one corner's truncation, measured along W —
the same quantity our `corner_fraction` names.** It is not a moderate lean; the
bracket in the diagram is unambiguous about what it spans. Confidence in this
specific point is high, resting on a labeled AGS diagram, cross-referenced by
identical terminology ("Corner Ratio," "the ratio of the corner width to the
width W") independently appearing in a granted US patent by a different
author — two organizations converging on the same definition and the same
name for it.

### Agrees / contradicts

- **Our value: truncation = 0.15 × width, per corner.**
- **Resolved trade figure: 0.135–0.145 × width per corner (0.14 preferred/typical),** —
  US10448713B1 (patent) + AGS naming-conventions diagram (definition), same
  quantity, cross-confirmed.
- **Contradicts, mildly.** Our corners are cut about 4–11% larger (relative)
  than the resolved range — a real, citable discrepancy, not noise, but not a
  large one: 0.15 sits just outside the 0.145 upper bound. Recommendation
  supportable by the sources: move toward **0.14**.

### Corner angle (45 degrees)

**Thin, secondary-sourced only — unchanged by this pass.** Trade education
pages (not primary/lab sources) state the emerald-cut corner is cut at 45° to
the edge (Ascot Diamonds; page returned HTTP 403 on direct fetch, reported
from a search snippet only). Neither the AGS naming-conventions document nor
US10448713B1 states a corner angle in degrees — both define corner *size*
(CR), not corner *angle*. AGS's diagram draws the corner as a single straight
bevel line (consistent with a flat 45°-style facet rather than a curve or a
two-facet corner), but the document gives no angle number. Our 45°
construction (equal truncation on both axes) remains the geometrically
simplest reading of "octagonal," visually consistent with the AGS diagram,
but not confirmed by a primary source stating the angle numerically.

### Does corner size vary with L:W, or between emerald and Asscher?

- **Within "emerald cut": not established.** The one patent with numbers
  (10,448,713) gives a single CR range (13.5–14.5%) alongside a single L:W
  range (1.35–1.40 in the worked examples) with no stated functional
  relationship between them — they read as independently-set parameters, and
  AGS's naming-conventions document lists them as two separate, independent
  parameters of "Emerald Cut Shape" with no cross-formula. No source in this
  pass showed CR varying systematically with L:W.
- **Emerald vs. Asscher: qualitatively yes, not quantified.** Multiple trade
  sources agree Asscher-cut corners are cut *more* deeply than emerald-cut
  corners ("Asscher cuts feature deeply trimmed corners... Emerald cuts
  consist of subtly trimmed corners"), consistent with Asscher's near-square
  L:W ≈ 1.0 vs. emerald's elongated 1.3–1.5 — but no source gave Asscher's CR
  number to compare against the 13.5–14.5% figure for emerald.
  [Estate Diamond Jewelry, "Emerald Cut vs. Asscher Cut"](https://www.estatediamondjewelry.com/emerald-cut-vs-asscher-cut-diamonds/)

### L:W range

**Agrees.** Our default range (1.30–1.50, default 1.40) sits comfortably
around multiple independent trade sources' "most desirable" range of
1.25–1.50 with 1.40 commonly cited as ideal, and inside the patent's claimed
1.325–1.425.
[Lumera Diamonds, "Emerald Cut Diamond Cut Guide"](https://www.lumeradiamonds.com/diamond-education/emerald-cut-diamond)

### The 0.227W trap

**Confirmed independently this pass — and confirmed NOT reusable.** IGS's own
HTML rendering of Jeff Graham's "Gram Easy Emerald" design (readable directly,
unlike the linked PDF, which remained OCR-unreadable in this pass) states
verbatim: **"The P5 steps on the second course are cut in until the width
across the face of the P3 facets on the first course is reduced to
approximately 0.227W, where W is the width of the stone."** and separately,
**"the closer the width of P3 comes to 0.227W, the closer your corners will
come to matching the relative proportions shown in the three views."** This
confirms both halves of the prior pass's finding: 0.227W is a **pavilion
facet cutting target (P3 facet width)**, and it is only *correlated* with
corner proportions as a byproduct of the cutting sequence — it is not itself
the plan-view corner-truncation fraction, and no arithmetic connects 0.227 to
the AGS/patent CR figure of ~0.14 in this design (they describe different
facets in different reference planes: P3 is a pavilion (bottom-facing) step
width partway down the stone; CR is a girdle-plane, top-down outline
dimension).
[IGS, "Gram Easy Emerald: Online Faceting Designs & Diagrams"](https://www.gemsociety.org/article/online-faceting-designs-diagrams-easy-emerald/)

---

## Confidence

- **Q1 (cushion): thin.** No primary or secondary source gives a number for
  corner radius, side bulge, or a fittable exponent. Trust the qualitative
  finding (two-radius rounded-rectangle construction, not a smooth
  superellipse, is the trade's actual mental model) over any number — there
  is no number. Do not treat `n = 3.0` as validated by this research; treat
  it as still eyeballed, now with an alternative construction family flagged
  for anyone who wants to chase real coordinates later.
- **Q2 (emerald): settled** on corner size, from two independent primary
  sources (a granted, specific utility patent giving the numeric range; the
  American Gem Society's own labeled diagram resolving what the quantity
  measures) that name the same parameter identically and agree with each
  other. **Thin** on corner angle (45°) — secondary trade sources only, one
  fetch blocked (403); neither primary source states an angle number.
  **Settled** on L:W range — multiple independent sources agree and our
  range sits inside all of them. **Settled** that 0.227W is unrelated to the
  outline (confirmed via a readable IGS mirror, not the original PDF).

## Numbers at a glance

| Quantity | Our value | Source value | Source | Call |
|---|---|---|---|---|
| Cushion corner radius / exponent | `n = 3.0` | none found | — | no basis either way |
| Emerald corner truncation (per corner, along W) | `0.15 × W` | `0.135–0.145 × W` (0.14 typical) | US10448713B1 + AGS naming-conventions diagram | **contradicts** (mildly) — consider 0.14 |
| Emerald corner angle | 45° | "45°" (secondary, unverified fetch) | Ascot Diamonds (via search snippet) | thin agreement |
| Emerald L:W | 1.30–1.50, default 1.40 | 1.25–1.50 general trade; 1.325–1.425 patent claim | Lumera; US10448713B1 | agrees |

**Note path:** `/Users/juanviljoen/projects/personal/ring-cad-app/docs/research/cut-outline-geometry-cushion-emerald.md`
