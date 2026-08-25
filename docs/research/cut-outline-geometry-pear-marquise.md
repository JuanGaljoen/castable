# Pear & marquise outline geometry, tip treatment, and prong conventions

Research pass for RNG-33 pointed-cut geometry (`ringcad/geometry/outline.py`,
prong distribution). GIA assigns no cut grade to fancy shapes, so throughout
this note "convention" means trade practice observed across multiple
independent sources, not a published standard — flagged explicitly wherever
that's the ceiling on confidence.

**Headline: the previous pass was partly right and partly lazy.** The two
*load-bearing outline formulas* (31% belly position, exact vesica tip angle,
V-prong 0.20× reach) genuinely have no published figure anywhere found in this
pass either — that part holds up. But the previous pass's broader claim of "no
published figure exists anywhere" was too strong: real trade data exists for
L:W ranges (GIA lab-submission statistics, not just marketing copy), for prong
*counts* (which contradicts our 4/6-only constraint), and for wing character
(qualitative but consistent, and it contradicts our straight-tangent-line
construction).

---

## Q1 — Pear outline

### Belly position (fraction of length from the round end)

**No published figure found.** Faceting design diagrams (Jeff Graham's
"Brilliant Pear 1.197", published via International Gem Society) give exact
proportions — `L/W = 1.197`, `T/W = 0.642`, `P/W = 0.428` (pavilion),
`C/W = 0.163` (crown), `H/W = 0.612` — but these are depth/table/crown/pavilion
ratios, not the belly's position along the length axis. No gemological or
faceting source found states "the belly sits at X% of the length."
**Our 31% (= 1/(2·1.60)) remains an invented value — confirmed, not refuted.**

- Source: [Brilliant Pear 1.197: Faceting Design Diagram, IGS](https://www.gemsociety.org/article/brilliant-pear-1-197-faceting-design-diagram/)

### Wing shape: straight, convex, or concave?

Trade guides consistently describe pear wings as **curved, not straight**:
GIA's own consumer-facing guide states a pear should have "gently rounded
shoulders and wings," and retail/gemological guides define the defects
symmetrically around a curved ideal — "bulged wings" (too convex, hides
weight), "flat wings" (too straight/concave-reading, "starves the outline"),
and "high shoulders" ("flat or angular shoulders... distort the classical
teardrop silhouette"). The consistent framing across independent sources is
that the correct wing is a **smooth continuous convex curve** between belly
and point, and a literal straight line reads as a defect ("flat").

**This contradicts our current construction** (straight tangent lines from
point to head circle). No source gives a construction formula or radius for
the correct curve — only the qualitative direction (convex, continuous,
between round-shoulder and flat-drawn-out-taper extremes).

- Sources: [GIA 4Cs — Pear Shaped Diamond: Tips for Picking the Perfect One](https://4cs.gia.edu/en-us/blog/pear-shaped-diamond-tips-picking-perfect-one/); [Frank Darling — Pear Shaped Diamond Guide](https://frankdarling.com/blog/the-ultimate-guide-to-the-pear-shaped-diamond/) (wings defined as "curves between belly and point"); consistent with [diamonds.pro](https://www.diamonds.pro/education/pear-shaped/), [michaelgabriels.com](https://michaelgabriels.com/pages/pear-diamond-guide) — all secondary/retail, but convergent and independent of each other.

### Head roundness

No source found states a numeric deviation from a true semicircle; all
describe it only as "rounded end." Treat "true semicircle" as an unverified
simplification, not contradicted, but also not affirmatively confirmed by any
source with a number.

### L:W range

Convergent across many independent trade/retail sources: **1.45–1.75**, with
stated buyer preference clustering near 1.55–1.60.

- Sources: [diamonds.pro](https://www.diamonds.pro/education/pear-shaped/), [Beyond4Cs](https://beyond4cs.com/shapes/pear/), [GIA 4Cs](https://4cs.gia.edu/en-us/blog/pear-shaped-diamond-tips-picking-perfect-one/) — retail-tier but mutually consistent, and matches the GIA 2009 trade/consumer preference survey referenced below (preferences peaking near 1.70, i.e. inside this band).

**Agrees with our range (1.45–1.75) and default (1.60).**

---

## Q2 — Marquise outline

### Two-arc (vesica-style) construction — is it real?

Multiple independent descriptive sources describe a marquise as "the
intersection of two circular arcs" / a lens shape, explicitly drawing the
connection to the vesica piscis construction (two circles of equal radius,
each centred on the other's perimeter... generalized to unequal centre
offset for non-60°-lens ratios). This is directionally consistent with our
two-arc construction. **However, every source found for this is retail/blog
tier** (no faceting-design primary source or GIA technical paper was found
stating the arc construction explicitly with a formula). Treat as
*corroborated in direction, not confirmed by a primary source* — the previous
pass's skepticism about a formula-bearing citation stands; what's new here is
that the two-arc *description itself* (not just our derived formula) does
turn up independently and repeatedly, which is more support than "we made
this up out of nothing."

- Sources: [Windy City Diamonds — The Marquise Diamond](https://www.windycitydiamonds.com/education/diamond-guide/marquise-diamond/); [Pardesco — Vesica Piscis](https://pardesco.com/blogs/news/vesica-piscis) (draws the explicit geometric connection); [3Soul — Marquise Guide](https://3soul.in/blogs/3soul/what-is-a-marquise-cut-diamond)

### Tip angle

**No published figure found**, anywhere, for either a target tip angle or a
minimum/maximum for durability. Our derived ~106° at L:W 2.0 / exactly 120° at
the vesica ratio remains **unverified — sources don't answer this.**

### L:W range

This is where real, harder data exists, and it's worth citing precisely
because ranges genuinely vary by source type:

- **GIA lab-submission data** (what diamonds cut in the real market actually
  measure): most commonly **1.6:1 to 2.2:1**.
- **Trade "preferred"/aesthetic range** cited independently by several
  sources: **1.85:1 to 2.1:1** (narrower, sitting inside the lab range).
- A 2009 GIA survey of 19 trade professionals + 25 consumers on fancy-shape
  L:W preference found preferences peaking around **1.70** across shapes
  (elongated relative to what the market commonly produces) — referenced
  secondhand via GoodStone; the original GIA publication was not located in
  this pass, so treat this specific figure as secondary-sourced.

Our range (1.75–2.30, default 1.95) sits **inside the GIA lab range** and
mostly inside the trade-preferred range (1.85–2.1); the default 1.95 falls
inside both. **Agrees**, though our upper bound (2.30) extends slightly beyond
both cited ranges — not contradicted, just uncorroborated at the tail.

- Sources: [GoodStone — What Nobody Explains About the Diamond Bow Tie Effect](https://www.goodstoneinc.com/blogs/news/diamond-bow-tie-effect-explained) and related GoodStone L:W pages (cite the GIA lab data and the 2009 survey); cross-checked against [Beyond4Cs marquise guide](https://beyond4cs.com/shapes/marquise/), [diamondscreener.com](https://www.diamondscreener.com/education/recommended-depth-table-and-length-width-ratio-for-fancy-shape-diamonds/).

---

## Q3 — Tip radius / keel tolerance

**No lab or cutting standard found stating a numeric tolerance for a tip
radius or micro-flat**, in GIA material, faceting literature, or findings
catalogues. What does exist, consistently: pointed tips are called out as the
most vulnerable point of the stone; a "bearded girdle" (hairline fractures
from cutting stress) is specifically flagged as a clarity/durability concern
concentrated at fancy-shape points; and the trade recommends **Medium girdle
thickness at the tips as a daily-wear minimum** (a girdle-thickness figure,
not a point-radius figure — different measurement, don't conflate). No source
makes the claim from the task prompt ("a visible radius at the tip is graded
a defect") either way — it is neither confirmed nor refuted.

**Verdict: sources don't answer this.** Zero-radius-vertex remains a modeling
choice, not a sourced one — matches the prior pass's finding on this specific
point.

- Sources: [Beyond4Cs — Diamond Girdle Thickness Explained](https://beyond4cs.com/grading/girdle-thickness/); [Bearded Girdle — Diamond Guidance](https://www.diamondguidance.com/education/diamond-grading/inclusions/bearded-girdle/); [Skyjems — Bearding](https://skyjems.ca/pages/encyclopedia-bearding)

---

## Q4 — Prong conventions

### Prong counts

**This is a real finding that contradicts our current constraint.** Trade
convention, converging independently across multiple retailers/setters:

- **Pear: 5 prongs is the standard convention** — 4 side claws + 1 V-tip at
  the point. 3-prong exists but is explicitly discouraged for security
  ("not recommended... especially at the pointed end"). Larger stones may go
  to 6.
- **Marquise: 6 prongs is the standard convention** — 2 V-tips (one per
  point) + 4 side claws (2 per side). A 4-prong version (1 V-tip per point +
  1 claw per side) exists for smaller stones.

Our system supports only 4 or 6 total prongs. **Marquise's 6-prong convention
fits that constraint exactly** (2 V + 4 claw = 6) and is effectively what our
"V-prong at every vertex + claws distributed by arc length" design already
produces at n=6. **Pear's 5-prong convention does not fit** — we'd need to
either allow 5, or accept that our 4/6 constraint forces pear onto a
non-conventional prong count (4 side + 1 V = 5 is the odd one out precisely
because pear has one vertex, not two).

- Sources: [Diamonds by UK — How Many Prongs for Pear Shaped Diamonds](https://diamondsbyuk.co.uk/blogs/engagement-ring/how-many-prongs-for-pear-shaped-diamonds-your-ultimate-guide-to-choosing-the-perfect-setting/); [PriceScope — 5 prong vs 3 prong claws for pear diamond](https://www.pricescope.com/community/threads/5-prong-vs-3-prong-claws-for-pear-diamond.247594/); [Brilliance.com — Pear Diamond Settings](https://www.brilliance.com/article/safe-diamond-pear-settings"); marquise: [The Diamond Reserve](https://thediamondreserve.com/diamonds/what-is-the-best-setting-for-a-marquise-diamond/), [RioGrande — Marquise 6-Prong Setting with Peg](https://www.riogrande.com/product/14k-white-gold-marquise-6-prong-setting-with-peg3/654055GP/) (an actual findings-catalogue SKU, i.e. closer to primary for "6 is a real manufactured configuration").

All of these are retail/forum-tier individually; the finding is the
**convergence across many independent, competing sellers**, which is the
strongest evidence available for an unstandardized trade convention (there is
no ISO document to cite instead).

### Side-prong placement (angles/positions)

No source gives numeric angles. Descriptive only: pear side claws sit "on the
stone's sides" (i.e., along the round head, away from the point); marquise
side claws are "two on each side curve," implying roughly symmetric placement
along each long edge rather than a stated angle. **This is consistent with,
not a validation of, our arc-length distribution** — no source contradicts
arc-length spacing, but none prescribes it either.

### V-prong dimensions (wrap distance, wall thickness, girdle-length reach)

**Confirmed: no published dimension exists**, including in the place most
likely to have one. Checked:

- Stuller, Rio Grande findings-catalogue product pages: give overall stone
  size and metal karat/finish, never V-tip wrap geometry.
- A working-jeweler technical article (Ganoksin, "V Prong Setting: To V or
  Not to V") gives only process guidance — cut seats "below AND above the tip
  of the stone," don't cut "more than 1/3 the thickness of the prong" when
  cutting the seat — no absolute mm figures for wrap distance, wall
  thickness, or girdle-length reach.

**Our 0.20× reach / 1.1mm floor remains an invented number — confirmed, not
refuted, exactly as the prior pass found.** This is the one place the prior
pass's "no published figure exists anywhere" claim holds up cleanly.

- Sources: [Ganoksin — V Prong Setting: To V or Not to V](https://www.ganoksin.com/article/v-prong-setting-to-v-or-not-to-v/); [Stuller Findings Catalog](https://www.stuller.com/findings-catalog); [Rio Grande product pages](https://www.riogrande.com/product/14k-white-gold-marquise-6-prong-setting-with-peg3/654055GP/)

### Cushion/emerald corners: V-prong or claw?

**The Stuller-attributed quote in the task prompt could not be verified
verbatim** — no Stuller-authored page turned up with that exact language in
this pass (search-only access, not a Stuller technical PDF fetch). What *is*
corroborated, independently and repeatedly, by working jewelers and forum
discussion (PriceScope, Weddingbee, retail setting guides) is the **substance**
of the claim: cushion-cut stones with rounded corners are hard to secure with
a single claw per corner because the stone can rotate, and the trade fix is
**double (claw) prongs per corner**, or a basket/gallery rail the pavilion
rests against, **not a V-prong**. Multiple sources are explicit that cushion
corners take *claw* prongs (often doubled), never V-prongs — V-prongs are
reserved for genuinely pointed vertices (marquise, pear, heart, princess).
Emerald-cut corners are not directly discussed in any source found in this
pass; by the same logic (a cut corner is a true vertex, not a rounded one)
our V-prong-for-emerald-corners choice is consistent with the stated
rule-of-thumb, but **no source explicitly names emerald-cut corners** —
that piece is an extrapolation, not a citation.

**Agrees with our cushion = claw choice.** Partially corroborates emerald = V
(by the same stated logic, not by an explicit statement). Recommends
considering **doubled claws on cushion corners** as a refinement we don't
currently implement, if rotation is ever a reported defect.

- Sources: [PriceScope — Rounded corners on cushion cut vs. more square](https://www.pricescope.com/community/threads/rounded-corners-on-cushion-cut-vs-more-square.229877/); [Weddingbee — Gallery rails, prongs & princess cuts](https://boards.weddingbee.com/topic/help-gallery-rails-prongs-princess-cuts/)

---

## Verdict summary

| # | Item | Our value | Verdict |
|---|------|-----------|---------|
| a | Pear belly at 31% of length | invented | **No published figure — confirmed unsourced, not refuted or corrected.** |
| b | Pear wings as straight tangent lines | modeled straight | **Contradicted** — trade sources consistently describe wings as gently rounded/convex curves; "flat" wings are a named defect. |
| c | Marquise as two-arc (vesica-style) intersection | modeled as such | **Directionally corroborated** by multiple independent descriptive sources, but no primary/faceting source gives the formula — construction shape agrees, the exact formula is still unverified. |
| d | Zero tip radius | modeled as sharp vertex | **Sources don't answer this** — no numeric tolerance found either way. Girdle-thickness-at-tip guidance exists but is a different measurement. |
| e | Prong counts (4 or 6 only) | our constraint | **Contradicted for pear** (trade convention is 5, not 4 or 6); **matches for marquise** (trade convention is 6, decomposing exactly as 2 V + 4 claw). |
| e | V-prong 0.20× reach / 1.1mm floor | invented | **No published dimension — confirmed unsourced**, including in the two catalogue sources most likely to carry one (Stuller, Rio Grande) and a working-jeweler technical article. |

L:W ranges: pear (1.45–1.75) **agrees** with our range/default; marquise
(GIA lab range 1.6–2.2, trade-preferred 1.85–2.1) **agrees** with our default
1.95 and mostly with our range 1.75–2.30 (our upper bound extends slightly
past both cited ranges, uncorroborated rather than contradicted).

## Confidence

**Thin, but not uniformly** — treat per-question:

- **Thin/unsourced** (trust nothing beyond what's stated): belly position
  fraction, marquise tip angle, tip radius tolerance, V-prong dimensions. No
  amount of further retail-blog searching is likely to surface these; a
  primary faceting-design source with dimensioned girdle-outline coordinates
  (e.g. a full Jeff Graham design PDF with the girdle polygon, or the GIA
  Fall 2024 G&G article and its companion "Length-to-width ratios among fancy
  shape diamonds" paper, both fetched-but-blocked in this pass — GIA's site
  timed out twice, ResearchGate returned 403) are the only places actually
  worth paying for/mirroring if this needs to be pinned down further.
- **Settled-by-convergence** (trust as trade convention, not as a technical
  standard — GIA grades no fancy-shape cut): L:W ranges for both shapes,
  pear = 5 prongs, marquise = 6 prongs, wings described as rounded not
  straight, cushion corners take claws not V-prongs.
- **Corroborated in direction only**: marquise two-arc construction (shape
  agrees across sources, formula does not appear in any of them).

**The note's path**: `/Users/juanviljoen/projects/personal/ring-cad-app/docs/research/cut-outline-geometry-pear-marquise.md`
