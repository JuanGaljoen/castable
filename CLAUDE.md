# Ring CAD App

Jewelry ring generator working toward one end goal: **upload any ring photo (or
enter parameters) and get a castable 3D model.** The app turns input into a
structured ring spec, generates a watertight 3D model, validates the mesh,
previews it in the browser, and exports a clean STL (and STEP) ready for lost-wax
casting. The solitaire is the first supported archetype, not the end goal; the
roadmap widens archetype coverage toward "any ring."

## Stack

- **Geometry kernel:** **build123d** (in-process Python, OpenCASCADE B-rep) —
  **the shipping kernel** as of RNG-15 (OpenSCAD cut over and removed). B-rep gives
  us `shell()` (real 3D wall-thickness enforcement), `fillet`/`sweep`/`loft`, curved
  surfaces, in-kernel geometry introspection, and STEP export — the capabilities
  OpenSCAD CSG cannot provide and that "any ring" requires.
- **IR / contract:** **RingSpec** — versioned, typed schema between the vision
  layer and the geometry layer; what the user edits; where castability rules
  validate (RNG-14).
- **Backend:** Python + Flask.
- **Castability gate:** Trimesh (watertight check + auto-repair) plus in-kernel
  `shell`/thickness checks on the B-rep.
- **Frontend:** Single HTML page, vanilla JS only (no frameworks).
- **3D preview:** Three.js with OrbitControls.
- **AI:** Claude API vision — photo → RingSpec (archetype, stone layout, shank
  profile, motifs, per-element dimensions, per-field confidence).

> **Migration note:** OpenSCAD (`scad/solitaire.scad`, `ringcad/render.py`,
> subprocess CLI) was removed in RNG-15 — `/generate-ring` now generates the
> solitaire in-process via build123d driven by RingSpec. The geometry lives in
> `ringcad/geometry/` (`shank`/`prong_setting`/`seat` + `build_solitaire` + STL/STEP
> export). The RNG-13 spike code under `spikes/rng13/` is retained for reference.

## Architecture (Path C: photo → castable model)

Five layers with one load-bearing artifact (RingSpec) in the middle:

1. **Vision / Understanding** — photo → RingSpec (Claude vision).
2. **RingSpec (the contract)** — versioned, typed; both sides evolve against it
   independently; carries castability validation rules.
3. **Procedural geometry** — RingSpec → geometry via a **library of composable
   modules** on build123d (`shank`, `prong_setting`, `seat`, `bezel`,
   `accent_seat`, `accent_prong`, `gallery`, …), each parametric and each
   emitting castable geometry. **Connectivity standard:** elevated settings
   (halo, trilogy, cathedral) attach via the reusable `gallery` primitive (the
   understructure that ties a raised setting to the shank/center for a single
   watertight manifold); pave / side-stone sets accents INTO the band instead.
4. **Castability gate** — `shell`/thickness, manifold, min-feature checks; much
   of it now in-kernel by construction.
5. **Export** — STEP (CAD interchange) + STL (print/preview).

**Core principle:** archetypes are **compositions of modules over a shared
spec, not monolithic templates.** Progress toward "any ring" = growing the
module vocabulary and composition rules, not piling up per-style templates.

## Casting Requirements (lost-wax)

These are hard manufacturing constraints, enforced in geometry, not just UI hints:

- Minimum wall thickness **0.8mm** throughout
- Minimum prong tip diameter **0.7mm**
- All modules must union into a **single watertight manifold**
- Exported STL must have **zero non-manifold edges**
- Mesh validated after every generation; auto-repair attempted if not watertight

## Solitaire Parameters (7)

These 7 parameters are the **solitaire archetype's slice of RingSpec** — the
first archetype, not the whole input model. RingSpec (RNG-14) generalizes beyond
these as archetypes are added.

| Parameter        | Notes                          |
|------------------|--------------------------------|
| `inner_diameter` | Finger size (mm)               |
| `band_width`     | Shank width (mm)               |
| `band_thickness` | Shank thickness (mm, >= 0.8)   |
| `stone_diameter` | Stone seat sizing (mm)         |
| `stone_height`   | Stone height (mm)              |
| `prong_count`    | **4 or 6 only** (dropdown)     |
| `setting_height` | Gallery/setting height (mm)    |

Modules (build123d, `ringcad/geometry/`): `shank()`, `prong_setting()`, `seat()`
composed by `build_solitaire(spec)` into a single watertight manifold.

## UI Design Specs

- **Layout:** single-view workspace on desktop — **no page scroll**. Sidebar on
  the left (~1/3: photo, then fields two per row, Generate/Download pinned at its
  foot); the 3D viewer fills the right ~2/3 at full height and is the centre
  piece. Base fields must fit at 1440x900 with no inner scroll, before AND after
  a generate; only detected features may push the sidebar body into its own
  scroll. Stacked vertically on mobile (<880px), page scrolls there.
- **Form:** inputs for all 7 parameters with sensible defaults; `prong_count`
  is a dropdown limited to 4 or 6.
- **Actions:** Generate button POSTs JSON to `/generate-ring`; Download STL
  button appears on success and keeps working after the viewer is added.
- **Viewer:** Three.js canvas, OrbitControls (orbit/zoom/pan), ambient + two
  directional lights, wireframe toggle button; re-renders on each new STL.
- **Mesh status:** indicator above the Download button - green "valid" /
  red "invalid". Download works regardless of validation status.
- **Errors:** error message displayed on generation failure.
- **Photo flow:** upload (jpg/png) -> `/classify-ring` -> form pre-filled with
  estimates. Show clear "Estimates only, verify before generating" label; every
  pre-filled field stays user-overridable. Fail gracefully on blurry/non-ring
  photos.
- **Accessibility:** WCAG 2.1 AA mandatory.

## API Endpoints

- `POST /generate-ring` - accepts either a structured RingSpec JSON body
  (`archetype` + its groups, e.g. `shank`/`setting`/`stones`/`halo` for the
  halo archetype, or `.../trilogy` for the trilogy archetype -> `validate_spec`
  -> `compose(spec)`) or, for back-compat, the flat 7 solitaire params with no
  `archetype` key (-> `from_params` -> `build_solitaire`). New archetypes are
  requested structured, per RNG-9; solitaire keeps both. Returns binary STL on success with `X-Mesh-*` headers;
  `?format=step` returns STEP (`model/step`). Castability violations and
  malformed input return a 400 JSON error naming the field. Geometry built
  in-process via build123d.
- `GET /health` - returns `{"status": "ok"}`.
- `POST /classify-ring` - accepts an image, returns Claude vision estimates
  toward a RingSpec (style/archetype, prong count, shank taper, features) +
  estimated dimensions.

## Rules

- TDD: RED -> GREEN -> REFACTOR. No production code without a failing test.
- Never rewrite working code to fix broken code; fix only the broken module.
- WCAG 2.1 AA mandatory for all UI work.
- No JS frameworks; vanilla only.
- Casting constraints (above) are non-negotiable.
- Never force push.
- **Checkpoint archetype builds at module seams.** Build each archetype in
  stages that follow the module-composition boundary — reusable primitive ->
  composition -> API/UI wire-up — and commit at each seam. Every checkpoint
  commit must be trustworthy on its own: tests green, no half-written module.
  A rate-limit interruption or aborted session must always leave the tree at a
  resumable commit, never mid-module. Prefer many small trustworthy commits
  over one large one. Extract genuinely reusable primitives (accent settings,
  pave beads) as their own unit; do not split a single archetype into
  contract/geometry/UI "tickets" — that is phase-gating dressed up as scope.
- **The form is a correction surface, not a configurator.** The end goal is
  *upload a ring photo and get a castable model of that ring*. The photo is
  the only thing that puts a FEATURE on a ring — the form's job is to let a
  user fix what vision got wrong (every dimension editable, a Remove on each
  detected feature), never to offer a catalogue of parts to assemble a ring
  from. RNG-24 built a feature picker twice — checkboxes, then an "Add a
  feature" disclosure — and both were rejected on sight: hand-picking
  features reads as a product configurator, and putting that above the
  dimensions greets the user with style selection before they have uploaded
  anything. The backend composability was never in question; only the picker
  was. **Adding a control is not the same as supporting a capability** — ask
  whether the photo can supply it before putting it in front of anyone.

## Tickets (Jira project: RNG)

**Done (base app, OpenSCAD path):**

- **RNG-1** OpenSCAD parametric solitaire ring template [Done]
- **RNG-2** Flask backend with STL generation endpoint [Done]
- **RNG-3** Vanilla JS frontend with ring parameter form [Done]
- **RNG-4** Three.js STL viewer with orbit controls [Done]
- **RNG-5** Trimesh mesh validation and auto-repair [Done]
- **RNG-6** Photo upload with Claude vision ring classification [Done]

**Foundation (build123d + RingSpec pivot — dependency-ordered):**

- **RNG-13** Spike: build123d proof-of-parity for the solitaire [Done]
- **RNG-14** RingSpec v1: structured ring IR / schema [Done]
- **RNG-15** Geometry kernel migration OpenSCAD -> build123d (solitaire cutover) [Done] - needs RNG-13, RNG-14
- **RNG-16** Procedural module library foundation (shank/prong_setting/seat/bezel) [Done] - needs RNG-15

**Castability hardening (pay down deferred by-construction debt before detail-heavy archetypes):**

- **RNG-17** Watertight by construction (eliminate auto-repair reliance) [Done] - needs RNG-16, blocks RNG-9

**Archetypes + vision (module compositions over RingSpec — built "the right way", no shortcuts):**

- **RNG-9** Halo ring style — real per-accent settings (not a shared-collar shortcut) [Done] - needs RNG-17
- **RNG-10** Three-stone (Trilogy) ring style [Done] - needs RNG-9 machinery
- **RNG-11** Side-stone band (channel/pave) [Done] - needs RNG-17, RNG-9
- **RNG-12** Vision -> RingSpec population (photo populates structured spec) [Done] - needs RNG-14, RNG-16; most valuable last, on the full catalog

**RNG-12 follow-ups:**

- **RNG-21** Enable the vision layer end-to-end (configure key + verify real photos) [Done] - relates RNG-12; turned it on with a real key, fixed the all-required-schema bug it exposed

**Fidelity depth (the current block — "looks like the photo", not more archetypes):**

- **RNG-18** Pin build123d + OCP in requirements.txt [Done] - a clean clone could not generate a ring; also found pydantic undeclared
- **RNG-23** Stone shape/cut in RingSpec (round + oval) [Done] - `StoneOutline` seam; unblocked RNG-26
- **RNG-22** Photo fidelity probe harness (repeatable photo -> model corpus run) [Done] - the measuring stick for everything below; found RNG-31/32/33 on its first run
- **RNG-25** Shank cross-section profile family (domed/flat/knife-edge outer x domed/flat inner) [Done] - needs RNG-16; the spec-widening half RNG-19 fenced off
- **RNG-27** Viewer presentation (metal material, studio lighting, tessellation) [High] - independent; perceived quality, touches no geometry
- **RNG-19** Geometry aesthetic refinement (proportions, claws, channel, halo) [Done] - surface polish behind the *existing* schema; four checkpoints, and the source of `docs/reference/` + ADR-0008
- **RNG-24** Composable features (halo + pave on one ring, retire the archetype union) [Done] - the architectural fix; a photo of a halo with pave shoulders now produces both instead of silently dropping one. Left `docs/adr/0013` and the configurator rule above
- **RNG-26** Vision estimates proportions from the image, not style averages [Medium] - **unblocked by RNG-23** (`length_ratio` is the first ratio it can fill)
- **RNG-30** 3D preview keeps stale geometry after the form changes [Medium] - misled RNG-23 QA twice; fold into RNG-27 if that lands first.
  The last member of the staleness family RNG-29 closed the rest of — and the one the
  feedback-lifetime rule does NOT settle: a rendered mesh is neither a claim about the
  input nor a caution about a value, so decide deliberately rather than by analogy
- **RNG-28** Accept WebP + HEIC uploads [Low] - deliberately deferred paper cut
- **RNG-29** Photo error message does not clear when a file is chosen [Done] - found in
  RNG-23 QA; established the feedback-lifetime rule below and the zero-install browser
  QA path. Also fixed `#photo-detections`, a second instance the ticket never reported
- **RNG-42** Band side-wall treatment (flat-sided court, soft square) [Low] - needs RNG-25; found by `docs/reference/band-profiles.png`, a third axis (side-wall/corner) the two-axis profile family doesn't express
- **RNG-43** Cathedral shoulders that sweep up to the head [Medium] - needs RNG-25 + RNG-16; split out of RNG-25 at Understand because it is setting attachment (the `gallery` connectivity standard), not a band cross-section

**Found by RNG-24 (2026-09-12):**

- **RNG-44** Pave retention for shoulder accents (bead-set, not channel) [Medium] -
  `SideStone.retention` is `Literal["channel"]`, so a photo showing pave-set
  shoulders gets a groove cut into the band instead. Found by uploading
  `probes/corpus/halo-round.png`: vision reads it correctly and says "pave"
  twice, and the contract is short by one value. RNG-11 deferred pave on
  purpose (Decision 5) and noted the widening would be additive; this is that
  widening. **Not the channel module with the walls removed** — pave holds
  each stone with raised beads of the band's own metal, closest precedent is
  the RNG-19 CP4 halo plate (build the body, cut the stones out, fuse the
  beads on). Get a `docs/reference/` sketch first (RNG-37 still open)

**Found by RNG-22's first live corpus run (2026-08-01):**

- **RNG-32** Vision estimates fields independently, producing specs the casting gate rejects [Done] - a stone taller than its own head; **revives the premise RNG-20 was deleted for**, now with a real counterexample
- **RNG-33** Stone cuts beyond round + oval (cushion, emerald, pear, marquise) [Done] - vision *said* "cushion cut" and had to write `round`; cashed in the RNG-23 `StoneOutline` seam. Left RNG-39/40/41 behind it
- **RNG-31** Vision intermittently reports no ring for a clear ring photo [Medium] - 1 failure in 4 runs of the same photo; diagnose before fixing
- **RNG-34** Close the side-stone gap in the fidelity corpus [Low] - needs a photo, no code

**Found by RNG-19 (2026-08-06):**

- **RNG-35** Trilogy side stones sit too far from the centre to read as one line [Medium] - CP1 fixed the TILT half and deliberately left the SPACING half, which the research calls the primary defect; a trilogy sketch in `docs/reference/` would make it easy to call done
- **RNG-36** Enforce the 2mm minimum band width at the shank's narrowest point [Low] - flagged unenforced in the research and still unenforced; may be the first legitimate non-`error` `Violation.severity`
- **RNG-37** Add reference sketches for solitaire, trilogy and side-stone [High] - no code, a file plus a table row each. `docs/reference/` has ONE sketch, and every RNG-19 defect was found by comparing a render against it while the suite stayed green. Trilogy first, since RNG-35 needs a target to judge against

**Found by RNG-33's archetype sweep (2026-08-21):**

- **RNG-39** Side-stone channel cut leaves degenerate geometry with an elongated
  centre stone [Medium] - **pre-existing, not caused by RNG-33**: an `oval` at
  `length_ratio` 2.5 on a channel band gives 2982 mesh bodies / 2712 non-manifold
  edges on the pre-RNG-33 tree, and the gate calls it castable. A `pear` at its
  conventional 1.60 leaves a zero-thickness double shell (bodies of -4.5236 and
  +4.5255mm3) at the groove tool's outer boundary. Non-monotonic in stone reach,
  so no `length_ratio` threshold can express it honestly - the fix belongs in
  `side_stone.py`, not in a gate rule

**Found by RNG-33's research pass (2026-08-24):**

- **RNG-41** Pear needs five prongs, and `prong_count` cannot express it [Medium] -
  trade convention for a pear is **5** (4 claw + 1 V-tip); `prong_count` is
  `Literal[4, 6]`, so the conventional pear is unbuildable. Suspected in CP3 (its
  design note already said "a pear asks for 5"), now sourced. Marquise's 6
  (2 V + 4 claw) **matches CP3 exactly**, so the gap is specific to pear. Not a
  one-liner: `_snap_prong` rounds vision to 4/6 and
  `coherence._repair_min_prong_tip` repairs by FORCING prong_count to 4

> **Two numbers we invented turned out to be published, and two research passes
> disagreed about that.** The first pass concluded "no published figure exists
> anywhere" for the whole `docs/research/` list; a second pass, run because that
> conclusion was disputed, found figures for the emerald corner (US10448713B1 +
> AGS, giving 0.14W where we had 0.15W) and for pear wing shape (straight is a
> *named defect*; correct wings are gently convex). The rest — pear belly,
> marquise tip angle, tip radius, V-prong wrap — really are unpublished, and the
> second pass checked the Stuller and Rio Grande findings catalogues to say so.
> **The lesson is about the shape of the claim, not the numbers:** "we searched
> and found nothing" and "nothing exists" are different statements, and writing
> the second when you mean the first closes a question that was still open. When
> recording a failed lookup, record *where you looked* — the second pass found
> the emerald figure in one search.


**Found by RNG-33 CP3 (2026-08-23):**

- **RNG-40** `expanded()` is not a true parallel curve, so offsets are short at
  sharp tips [Medium] - it grows the semi-axes instead of offsetting the girdle
  (both `OvalOutline` and `ProfileOutline` document the approximation and say
  the error is largest at the tips). At a marquise point the seat wall's true
  clearance is **0.426mm at `length_ratio` 1.95 and 0.388 at 2.30** against a
  nominal 0.51 and a 0.46mm claw node sphere, so the sphere GRAZED the wall and
  OCCT resolved it as a zero-volume lamina: 2 mesh bodies, 184 non-manifold
  edges, off a single valid B-rep of the right volume (docs/adr/0007). CP3
  worked around it by raising `GIRDLE_EMBED` 0.06 -> 0.15, which is not a fix:
  pear is safe by passing fully THROUGH the wall (0.159mm) while marquise is
  safe by clearing it, so **no single constant states the requirement
  honestly**. Also owns the halo plate, which uses the same `expanded()`

> Removed in the pivot: RNG-7 (cathedral shoulders, OpenSCAD-specific) and RNG-8
> (style registry over OpenSCAD) were deleted — both are superseded by the
> RingSpec + module-library foundation. **RNG-20** (vision spec castable by
> construction) was deleted on 2026-07-20: its premise was disproved — a probe of
> real photos generated 3/3 watertight with zero repairs, so it was solving a
> hypothetical.

## Current Phase

> **Where we stand (2026-09-12):** the archetype catalogue is complete, vision is
> live, centre stones can be oval end to end (RNG-23), fidelity is measurable
> (RNG-22), **the geometry reads as jewelry rather than as fused primitives**
> (RNG-19), **the vision layer emits buildable specs** (RNG-32: 5/5 corpus
> photos generate, up from 3/5), and **a ring is no longer one archetype**
> (RNG-24: a photo showing a halo AND pave shoulders now produces both).
> What remains in the fidelity block is **presentation** (RNG-27, still the
> cheapest large win and touches no geometry) — **vocabulary** (RNG-33 stone
> cuts, RNG-25 shank profiles) is done on both fronts.
>
> **The honest gap is retention, not archetypes.** RNG-24 closed the "we can
> only say one thing about a ring" problem; RNG-44 is the next one down —
> vision reads pave shoulders correctly and `retention` can only say
> `channel`, so the stones land in the wrong setting style. Detection is
> ahead of vocabulary again, which is the same shape as the RNG-23 gap
> (vision said "cushion" and had to write `round`).
>
> **The lesson RNG-19 leaves is about how defects get found here.** Four real
> defects — including a halo passing the casting gate with a quarter of the
> minimum metal between stones — sat behind a fully green 3488-test suite. None
> was found by a test. Every one was found by **comparing a render against a
> trade reference sketch**. So: `docs/reference/` holds design-target sketches
> per archetype (semi-mounts — bare metal, no stones, exactly what we render),
> and it currently has **only `halo.png`**. Getting solitaire / trilogy /
> side-stone sketches is the highest-leverage non-code task on the board;
> adding one is a file plus a table row. See `docs/adr/0008`.

**RNG-9 (halo), RNG-10 (trilogy), and RNG-11 (side-stone) complete.**

Done and merged: RNG-13 (spike, GO), RNG-14 (RingSpec v1), RNG-15 (kernel cutover
to build123d), RNG-16 (module library), RNG-17 (watertight by construction: raw
geometry castable by construction, not repair-reliant), RNG-9 (halo archetype —
RingSpec discriminated union, `accent_seat`/`accent_prong` primitives, the
reusable `gallery` primitive, `/generate-ring` + frontend wiring).

**RNG-10 (trilogy) complete:** two symmetric side settings (`accent_seat` + 4
`accent_prong` each) on a gallery-post pedestal (the gallery's hub alone — a
single flanking stone has no ring for a rail), placed by `placement(c)` rotated
by the derived angular offset. Checkpoint 1 (contract) — `TrilogySpec` union
member + `_trilogy_overcrowding` (see `docs/adr/0003`: classify a field as
placement vs. wall before writing a model-level proxy for it). Checkpoint 2
(composition) — `ringcad/geometry/trilogy.py`, `check_trilogy`,
`MODULES`/`ARCHETYPES["trilogy"]`. Checkpoint 3 (wire-up) — trilogy `<option>`
+ `#trilogy-fields` in the form, an archetype registry in `static/app.js` (a
registry not an if-chain, since trilogy is the second non-solitaire archetype).
The frozen design lives in `specs/RNG-10.md`.

**RNG-11 (side-stone) complete:** a symmetric channel-set accent row down each
shoulder — `accent_seat` beads at `_accent_angles`/`_accent_loc` placements
retained by two continuous channel-wall rails (partial `Torus` arcs), welded
THROUGH the shank (no `gallery`, no `accent_prong`; the RNG-9 CP3 pave/side-stone
connectivity mode). Checkpoint 1 (contract) — `SideStoneSpec` union member +
`_side_stone_overcrowding` (`retention` is `Literal["channel"]`; pave deferred).
Checkpoint 2 (composition) — `ringcad/geometry/side_stone.py`, `check_side_stone`,
`MODULES`/`ARCHETYPES["side_stone"]`. Checkpoint 3 (wire-up) — side-stone
`<option>` + `#side-stone-fields` (incl. the `retention` `<select>`), a
`stringKeys` addition to the `static/app.js` archetype registry (for the
retention select). The frozen design lives in `specs/RNG-11.md`.

**RNG-12 (vision -> RingSpec) complete:** an uploaded photo now populates a full,
schema-valid RingSpec (archetype + groups + per-field confidence) and the form is
a structured editor over it. Backend: `classify.py` `RingClassification` gains an
`archetype` enum + `RingConfidence`; `ClassifyResult.to_spec()` assembles a
`validate_spec`-checked spec (shared dims over defaults, `inner_diameter` never
estimated, group dims clamped to the RingSpec field bounds read off the models,
confidence clamped to [0,1], solitaire fallback on `ValidationError`); `to_json()`
/ `/classify-ring` return `{ring_detected, detected_style, note, spec}`. Frontend:
`photo.js` selects the detected archetype and pre-fills every field, flagging
shared fields with confidence < 0.5 (amber marker + aria note). Built as two
commits on one branch (backend, frontend), not per-checkpoint PRs. The frozen
design lives in `specs/RNG-12.md`.

**RNG-21 (enable vision end-to-end) complete:** ran the vision layer against a
real API key for the first time and fixed what only the real path exposed.
Config: `.env` now loads at startup via `python-dotenv` (`load_dotenv()` in
`create_app()`; explicit exports still win). Bug found + fixed: the
`RingClassification` structured-output schema had ~24 *optional* (defaulted)
fields, which the real Messages API rejects (400 on `float | None` unions) and
then, once unions were cut, *hangs* on (exponential compile cost from the
present/absent field combinations). Fix: **every schema field is required, no
defaults**; `0` is the "not estimated" sentinel the parser reads, and the prompt
tells the model to fill every field. Offline guard `tests/test_classify_schema.py`
asserts zero optional fields + the 16 union cap — the tests that catch it without
a key. Because every classify test stubs the client, this shipped invisibly
through RNG-6/12; see `docs/adr/0004-structured-output-schemas-need-all-required-fields.md`
(all-required rule + "verify against the real API once"). Verified live on a real
solitaire photo (correct archetype/4-prong, five estimable dims adjusted, ~4s,
confidence 0.60–0.95). **Decisions recorded: keep Haiku as the default model;
keep the 0.5 confidence-marker threshold.**

**Roadmap checkpoint (2026-07-20): breadth -> depth.** With the vision layer live,
real photos were run end-to-end through `/classify-ring` -> `/generate-ring`
(`spikes/rng22/probe_vision.py`, the RNG-22 prototype). Findings:

- **Castability is not the problem.** 3/3 real ring photos generated as raw
  watertight manifolds, `X-Mesh-Repaired: false`. RNG-20's premise was
  hypothetical; it was deleted rather than built.
- **Fidelity is the problem, and it is a vocabulary gap, not an archetype gap.**
  Two of three photos had *oval* centre stones and we built round ones — `Stones`
  has only `stone_diameter`/`stone_height`, so every ring ever generated is a
  round brilliant (-> RNG-23).
- **The archetype union loses information the classifier already has.** A halo
  photo read as "halo ... with pave-set accents along the shoulders"; the
  discriminated union forced one choice and the shoulders vanished. The union
  quietly reintroduced the "monolithic templates" this file's core principle
  rejects (-> RNG-24).
- **Vision recalls genre averages rather than measuring.** Its own note: "dimensions
  estimated from standard proportions for this style". Absolute mm are
  unknowable from a photo; *ratios* are visible and currently discarded (-> RNG-26).
- **"Looks bad" is two problems:** geometric fidelity (RNG-23/25/19) and
  presentation — flat grey material, validation-grade tessellation (-> RNG-27).

**RNG-18 (dependency pinning) complete:** `build123d`, `cadquery-ocp-novtk` (the
OpenCASCADE binding — *not* "OCP") and `pydantic` are now declared and pinned; a
clean venv installs and runs the full suite with no manual steps.
`tests/test_requirements.py` walks the real AST of `ringcad/` and fails on any
undeclared or unpinned import, so this class of gap cannot return silently.

**RNG-23 (stone shape) complete — round + oval end to end.** An uploaded oval
photo now produces an oval castable model, and shape is an editable field on every
ring style.

- **The seam is `ringcad/geometry/outline.py`.** `StoneOutline` answers `wire()`,
  `prong_angles()`, `frame_at()`, `half_width()`, `min_curvature_radius()`,
  `expanded()`, `angles_by_arc()`, `tube()`. Consumers split two ways:
  **curve-walkers** (`seat`, `bezel`, `prong_setting`, `halo`) take the path and
  frames; **width-consumers** (`trilogy`, the overcrowding checks) take a
  half-width only. `c["stone_r"]` survives *only* for scale-derived values (peg,
  hub radii), never for anything that follows the girdle. **A new cut is a new
  outline class, not an edit to six modules** — that is the whole point.
- **Contract:** `Stones.shape` (`round`|`oval`) + `length_ratio` (1.0–2.5), both
  defaulted, so pre-RNG-23 specs are untouched. `stone_diameter` is the **short**
  axis. A ratio (not a length) because a ratio is what a photo shows.
- **Conventions worth keeping:** prongs sit so the tips fall midway between claws
  (`θ = tip + (k+0.5)·2π/n` — the 10-2-4-8 oval layout at n=4); halo accents are
  spaced by **arc length**, since equal angles bunch them at the tips; round keeps
  its literal `Torus` call so circular seats are bit-identical.
- **New castability rule:** `stone_curvature` — a tube swept along a curve tighter
  than its own section radius passes through itself, so
  `(stone_diameter/2)/length_ratio` must clear the 0.45mm seat collar.
- **`docs/adr/0005`** — a fuse that silently DROPS bodies still reports watertight,
  zero non-manifold edges, and passes every casting floor, because the offending
  metal is gone. Assert volume, not just watertightness.
- **`docs/adr/0006`** — when a scalar becomes a shape, audit *every* consumer;
  **validation gates need it more urgently than builders** (a wrong builder is
  visible, a wrong gate is silent). Three separate gates were still measuring the
  short axis.

> **The lesson that generalises:** three RNG-23 bugs passed a fully green
> 3413-test suite and were caught by a real photo and a screenshot — including the
> *default* ring style silently discarding the chosen shape (solitaire took the
> legacy flat-7 request path, which has no `stones` group). Each was a test written
> against the author's assumptions rather than against what a user gets. **Run the
> real path before calling shape/vision work done.**

**RNG-22 (photo fidelity probe harness) complete — the fidelity block is now
measurable.** `python probes/fidelity_probe.py` runs a committed corpus of real
ring photos through the *real* endpoints (`/classify-ring` -> `/generate-ring`,
so the magic-byte sniff, spec assembly, casting gate and mesh check are all in
the path) and reports per photo. Geometry lands in `probes/output/` (gitignored)
so a render can be opened beside the photo it came from.

- **Pure core, thin I/O shell.** `load_manifest` + `evaluate` hold the corpus
  semantics and the whole failure bar and need no key, no network, no photo — so
  they are tested offline in the normal suite (`tests/test_fidelity_probe.py`,
  `tests/test_fidelity_verdict.py`) while the harness itself stays a standalone
  script pytest never collects. A pytest marker would have needed registering
  (there is no pytest config) and could still be run by accident; a script cannot.
- **The failure bar is generation, deliberately.** An archetype mismatch is real
  signal and is reported prominently but stays **amber** — a genuinely ambiguous
  photo must not make the harness cry wolf. A declared manifest entry with no
  photo behind it is a reported **gap**, not a failure. **Adding a photo is a
  manifest entry plus a file — no code change.**
- **It cost ~2 cents and found three product defects on its first run** (RNG-31,
  RNG-32, RNG-33) plus two bugs in itself, none visible to the then-3426-test
  suite. Timings: 15–56s per photo, of which the API call is ~4s — the rest is
  B-rep generation. STLs are 6–48MB at validation-grade tessellation (relevant to
  RNG-27).

> **The lesson, again, sharper:** RNG-23 taught "run the real path before calling
> shape/vision work done". RNG-22 is that lesson turned into a tool, and it
> immediately proved itself: **a deleted ticket came back.** RNG-20 was deleted on
> 2026-07-20 because 3/3 real photos generated clean; the fourth photo produced a
> stone taller than its own head (-> RNG-32). Three samples looked like evidence
> and were an anecdote. When deleting a ticket on empirical grounds, note the
> sample size in the obituary.

**RNG-19 (geometry aesthetic refinement) complete — four checkpoints.** The
generated rings stopped reading as parametric primitives.

- **CP1 proportions.** The shank flared 70% at the head in *both* width and
  thickness; it now tapers in width (`SHANK_WIDTH_TAPER` 1.35) with thickness
  near-constant (1.15). Trilogy side stones were each rotated a full 51° so their
  tables faced sideways off the finger — span 32.8mm → 27.2mm.
- **CP2 claw finishing.** Claws were constant-width wire ending in a ball *wider
  than the claw itself*; now a continuous taper to a domed tip (`docs/adr/0007`).
- **CP3 channel setting.** Was raised `Torus` collars — halo geometry where its
  premise does not hold, since channel setting has **no per-stone collar by
  definition**. Now a groove cut into the band.
- **CP4 halo plate.** Was N collar tubes 0.7–0.8mm around 1.2mm stones, pinned at
  the casting floor so no tuning could slim them. Now one continuous plate with
  the seats bored into it, hanging off the centre claws — **no gallery at all**.

**`docs/adr/0008` is the reusable half:** we render metal only, so a setting *is*
the negative of its stones — **build the body and cut the stones out** rather
than assembling setting parts. CP3 and CP4 are both that move. Assembling sizes
every retaining feature independently at its own floor, so metal accumulates into
collars nothing can slim; cutting makes the remaining metal whatever the bores
leave. It is also safer: a cut has no tangency to crack along, and cannot open a
solid unless it severs it. **Its trap: a bore that fails to OPEN becomes a sealed
void that still reports watertight, single-solid, all floors met — so assert mesh
BODY COUNT on subtractive modules** (the sibling of ADR-0005).

**Four latent defects fixed, none visible to the suite:** the castability check
and the builder disagreed about the shank taper (ADR-0002 drift, so setting the
field moved the check but not the model); `_halo_overcrowding` only checked that
accents do not *overlap*, so a halo passed with **0.195mm** between seats;
`check_gallery` was the halo's in-kernel check and worked by finding rail faces,
so once the rail went it passed everything; and `compose` subtracted cuts
iteratively, raising `Null TopoDS_Shape` on a 13-accent halo (one `cut(*tools)`
fixes it — ADR-0001's single-general-fuse lesson, applied to subtraction).

**Two process notes worth more than the code.** (1) *Numbers set by eye get
written up as principles.* The halo web rule was relaxed after a visual
complaint, and researching it confirmed the change but found the stated reason
was wrong AND that a second number — the plate rim — had been eyeballed to half
the trade figure. **Look the number up; do not argue it.** (2) *Verify the dev
server is younger than the edit.* It runs with reload off, so "I see no change"
was twice a stale process, not a bad build.

**Next:** **RNG-27** (material + lighting) is still the cheapest large win and
touches no geometry; with RNG-19 and RNG-32 both landed, the remaining "models
look flat" complaint is presentation, not proportion or castability.
**RNG-44** (pave retention) is the sharpest *fidelity* gap — it is the one
place a real corpus photo is still visibly set the wrong way. **RNG-26** is
unblocked (`length_ratio` is the first ratio vision can fill), and **RNG-35**
finishes the trilogy spacing RNG-19 CP1 half-did. Run the probe before and
after each of them — and **get a reference sketch for whichever archetype you
touch** (`docs/reference/`), because that, not the suite, is what caught every
RNG-19 defect.

**RNG-32 (vision cross-field coherence) complete.** A vision-assembled spec can
now be schema-valid and individually defensible on every field yet physically
impossible together (a 5.2mm stone in a 3.0mm head); `to_spec()` used to hand
that straight to the casting gate and let it fail. It no longer does.

- **The repair is driven by the casting gate's own `Violation`s, not a
  restated table of containment pairs** (`docs/adr/0009`). `ringcad/ringspec/
  coherence.py`'s `make_coherent(spec, confidence)` assembles → validates →
  repairs whichever field each `Violation` names, to the value it names → 
  re-validates, bounded at 6 passes. All 11 current gate codes have a repair;
  a future gate rule is covered for free, the way a parallel table never
  would be. Two codes have a genuinely ambiguous victim
  (`stone_exceeds_head`, `min_prong_tip`); per-field vision confidence
  (already collected, previously only used for the low-confidence UI marker)
  picks which sibling moves, defaulting to a fixed victim on a tie.
- **Fallback chain, not a single repair attempt:** detected archetype
  repaired → solitaire from the same shared estimates repaired → pure-default
  solitaire (proven castable for all four archetypes by test). Verify's fuzz
  testing found a genuine case the repair loop alone cannot converge on —
  two gate rules pulling the same field in opposite directions, individually
  satisfiable, jointly impossible (`docs/adr/0009`) — which is exactly why
  the fallback chain, not the repair function, is what actually guarantees a
  castable result.
- **`to_json()` now returns `adjustments`**, and `static/photo.js` marks any
  field the repair moved with a dashed-indigo border and its own note,
  visually distinct from the existing amber low-confidence marker (WCAG 2.1
  AA 1.4.1 — not colour alone). Browser-QA'd against a live dev server:
  uploaded photo → marker renders → Generate → castable mesh.
- **RNG-22 probe: 5/5 corpus photos now generate**, up from 3/5, including
  the ticket's own counterexample (`halo-round.png`). The other two
  fixed by this ticket had been silently broken by RNG-19 tightening the
  gate — vision emitting buildable specs had stopped being hypothetical.
- **`docs/adr/0010`** is the sharper lesson: a regression test written for
  this ticket, in this session, passed — and was wrong. It claimed to
  reproduce the jointly-infeasible case above by constructing a
  `ClassifyResult` directly, but `_assemble` normalises stone shape on
  *every* attempt, not only the last resort, so the scenario the test's own
  docstring described never actually occurred; the first attempt converged
  for an unrelated reason. Caught by tracing the passing test by hand, not
  by any assertion failing. **A test authored in the same sitting as the
  code it tests is not exempt from being traced** — the same discipline
  ADR-0005/6/7 already apply to the gate itself.

**RNG-25 (shank cross-section profile family) complete.** The band was
exactly one shape — a hardcoded `Ellipse(th/2, w/2)` — regardless of what a
photo showed; it is now six trade profiles across every archetype.

- **The ticket's own four-name list was wrong, and research caught it before
  any code was written.** "Comfort fit" is not an outer shape at all — it is
  purely a domed INNER surface, and the trade pairs it with every outer shape
  independently (Stuller stocks "Half Round Comfort Fit" and "Comfort-Fit
  Heavy Knife Edge" as separate SKUs). The schema is two independent fields,
  `Shank.outer_profile` (domed/flat/knife_edge) x `inner_profile`
  (domed/flat), not one five-name enum. `domed`+`domed` is `court` — today's
  literal ellipse, kept bit-identical (confirmed by SHA-256 hash against the
  pre-RNG-25 tree for the golden solitaire, halo, trilogy AND side-stone).
  "Graduated" turned out not to be a band shape at all — the trade uses it
  for accent-stone sizing along a band; the real term for a narrowing band is
  "tapered," which is `Shank.shank_taper` and already shipped. That scope
  item was dropped, not built. Full sourcing in
  `docs/research/shank-cross-section-profiles.md`.
- **A trade reference sheet (`docs/reference/band-profiles.png`) corrected
  the schema again, after research already had.** It confirmed every profile
  RNG-25 built, and it drew a THIRD axis (the band's side walls — court vs.
  flat-sided court, flat vs. soft square) the two-axis schema cannot express.
  Filed as RNG-42 rather than folded in — the pattern `docs/reference/`
  exists for (ADR-0008's directory) keeps finding real gaps before a render
  does.
- **A genuine self-intersection bug, found by tracing the math by hand before
  any geometry was built.** The first cut at the taper formula receded each
  non-flat surface by a fixed 0.5 regardless of its partner — correct only
  when BOTH sides are non-flat (court, splitting the ellipse's taper 50/50).
  `knife_edge` + `domed` (the one pairing with no reference-sheet cell to
  catch it by eye) produced negative thickness near the band's edge. Fixed by
  sharing the taper amplitude across however many surfaces are non-flat
  (`SectionProfile.weights()`), proven — not spot-checked — to keep thickness
  non-negative everywhere. Verify mutation-tested the guard test against the
  actual original bug (checked out the pre-fix commit) to confirm it wasn't
  asleep.
- **The knife-edge minimum edge width needed no gate rule at all**
  (`docs/adr/0012`). The ticket asked for a castability check the way every
  other floor in this file works; building the ridge as an actual two-slope
  shape showed the apex could instead be sized so a too-thin value is not
  constructible (`knife_edge_apex_fraction` always yields exactly
  `MIN_WALL_MM` of flat crown). No new `Violation` code, no new
  `make_coherent` repair path — RNG-32's whole coherence machinery needed
  zero changes.
- **`_min_wall`'s own floor turned out to already be violated, correctly, by
  every ring this app has ever shipped** (`docs/adr/0011`). It checks the
  `band_thickness` FIELD; the actual court section tapers to zero thickness
  at the band's own edges by design (the trade sheet confirms this is normal
  — it's what "court" IS). The ticket's "min wall holds across the full
  parameter space" was rewritten to name the centreline explicitly, at Design,
  before it could ship as a criterion nothing could actually satisfy.
- **`head_r` (the band's outer radius at the head, where every setting welds
  in) is now one function** (`sections.head_r`), called by both
  `castability.py` and `geometry/_common.py` — the exact drift class that bit
  `shank_taper` once already (ADR-0002) closed for this field before it could
  recur.
- Verified against the real dev server, not just the stubbed suite: all six
  profile combinations generate through `/generate-ring` as raw watertight
  manifolds needing no repair, including the previously self-intersecting
  `knife_edge`+`domed`. Full suite: 3923 passed.
- **RNG-42** (band side-wall treatment) and **RNG-43** (cathedral shoulders)
  filed as follow-ups rather than folded in — both are real scope the ticket
  surfaced, neither is a band cross-section.

**RNG-24 (composable features) complete — the archetype union is retired.** A
ring is a base (`shank`/`setting`/`stones`) plus whichever of
`halo`/`trilogy`/`side_stone` are present, any subset. The union had quietly
reintroduced the "monolithic templates" this file's core principle rejects,
and it was measurably losing information: real corpus photos read as
halo-with-pave-shoulders and the shoulders vanished, because the contract
could hold only one answer. **Verified end to end on the real path** — an
upload of `probes/corpus/halo-round.png` now detects `['halo', 'side_stone']`
and generates a single raw watertight manifold, no repair.

- **CP1 contract.** One `RingSpec`, optional feature groups. A legacy
  `archetype` tag is translated at the `validate_spec` edge, so every existing
  spec, the flat-7 path and the corpus keep working. `spec_errors` lost its
  union-tag handling; six `isinstance(spec, XSpec)` guards became presence
  checks, which is what they always meant.
- **CP2 cross-feature castability.** `compose` builds from the feature set;
  `ringspec/footprint.py` is the shared currency — each feature reports the
  annular sector it occupies, and one generic pairwise check replaces a table
  of per-pair rules that would grow quadratically. `_SIDE_STONE_A_START_DEG`
  stopped being a constant and became *derived*: a halo sharing the head
  pushes the accent row further round, and the gate and the builder read the
  same derived value (ADR-0002's drift class, closed before it could open).
- **CP3 vision + UI.** `classify.py` emits a feature SET, not one nearest
  archetype. The form now offers **no way to add a feature at all** — see the
  configurator rule under `## Rules`, which this ticket paid for twice.

**Two lessons, both about things a green suite cannot tell you.**

1. **`docs/adr/0013` — a back-compat shim outlives its own premise.** CP1
   re-attached a single `archetype` label to the dumped spec as a courtesy to
   callers, documented as "meaningful only while at most one feature is
   present", deferred to CP3. CP3 is the checkpoint that made multi-feature
   real, and the shim rode into it unchanged: on a halo+side_stone spec the
   label is `"halo"`, re-validating that dict takes the LEGACY exclusive path,
   and it rejects the spec for also carrying `side_stone`. **The spec poisoned
   itself passing back through its own validator** — a 500 on the first real
   upload, behind 3900 green tests, because every fixture had at most one
   feature. *When deferring a migration, write the test that goes red when the
   deferral expires.* A comment is a note to a reader who may never come.
2. **The picker was never the ticket.** The UI was built twice (checkboxes,
   then an "Add a feature" disclosure) and thrown away twice, while the
   backend half — the part that actually stops a photo losing its shoulders —
   was never in question. The end goal is reproducing a photographed ring, so
   the form is a correction surface; a parts catalogue is a different product.

**RNG-29 (stale photo feedback) complete.** The status line under "Estimate from
photo" outlived the condition it described: it said "Choose a JPEG or PNG photo
first." while a valid JPEG sat visibly in the input. Cosmetic in code, genuinely
misleading in use — it cost real time in RNG-23 QA, where element ids and script
syntax were checked before anyone realised the message was simply stale.

- **The rule, which is the reusable half: feedback about an input must not
  outlive that input's value — but "feedback" splits two ways.** *Claims about
  the file* (the status line, `#photo-detections`) die with the file, because
  they assert something no longer true. *Cautions about values* (the amber
  low-confidence and indigo adjusted markers) survive, because the values they
  caution about are still sitting in the form — **dropping a caution while its
  suspect value stays is worse than a stale caution.** `applySpec` already
  clears those on the next successful run, when the values change too.
- **A second instance the ticket never reported.** `showDetections` un-hides
  `#photo-detections` and nothing ever re-hid it, so choosing a different photo
  left "Detected: oval solitaire" asserting the *previous* photo's style. Found
  by applying the rule above to every element in the panel rather than only to
  the one in the bug report.
- **The generate side was checked, as the ticket asked, and was already nearly
  right.** `clearResult()` retires both the banner and the field markers on
  every submit. The residual was narrow: the field stayed red while the user
  typed the correction the message had asked for. Fixed for the marker only —
  **the banner carries the instruction being followed ("must be at least
  0.8mm") and must survive the keystrokes that satisfy it.** A state indicator
  dies with the value; an instruction does not.

> **The lesson is about how this was proved, not about the fix.** The house
> style for frontend work is Python source-inspection (`tests/test_frontend_*.py`),
> which for a DOM-event bug can only show the listener is *wired*, never that it
> *fires* — so the four new tests are honest about that in their own docstring
> and are not the evidence. The evidence is a browser, and **it needed no new
> dependency**: `playwright` is already in the venv, and
> `p.chromium.launch(channel="chrome")` drives the system Chrome with no
> browser download, against the real dev server. The script lives in the
> scratchpad, so `requirements.txt` and `tests/test_requirements.py` are
> untouched. **Then mutation-test the QA script itself** — `git stash push` the
> fix, rerun, `git stash pop`: four target checks went red and three deliberate
> controls stayed green. A QA script never run against the broken code is just
> a script that passes. Committing this harness properly (declaring playwright,
> owning browser setup in CI) is a real ticket, not a rider on a Low paper cut.

**Filed, not built: RNG-44 (pave retention).** Vision reads the corpus photo's
shoulders as pave-set, correctly, twice — and `retention` is
`Literal["channel"]`, so the app sets them the wrong way. The stones are
genuinely there; the setting style is wrong. That is the honest state of
shoulder fidelity today.
