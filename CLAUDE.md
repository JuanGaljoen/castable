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

- **Layout:** form on the left, 3D viewer on the right (desktop); stacked
  vertically on mobile.
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

- **RNG-18** Pin build123d + OCP in requirements.txt [High] - a clean clone cannot currently generate a ring
- **RNG-22** Photo fidelity probe harness (repeatable photo -> model corpus run) [High] - the measuring stick for everything below; relates RNG-12
- **RNG-23** Stone shape/cut in RingSpec (oval, emerald, cushion, pear, marquise) [Highest] - needs RNG-14, RNG-16; blocks RNG-26
- **RNG-25** Shank profile family (knife-edge, cathedral, comfort-fit, graduated) [High] - needs RNG-16; the spec-widening half RNG-19 fenced off
- **RNG-27** Viewer presentation (metal material, studio lighting, tessellation) [High] - independent; perceived quality, touches no geometry
- **RNG-19** Geometry aesthetic refinement (fillets, surfaces, proportions) [High] - surface polish behind the *existing* schema
- **RNG-24** Composable features (halo + pave on one ring, retire the archetype union) [Medium] - the architectural fix; needs an ADR
- **RNG-26** Vision estimates proportions from the image, not style averages [Medium] - needs RNG-23
- **RNG-28** Accept WebP + HEIC uploads [Low] - deliberately deferred paper cut

> Removed in the pivot: RNG-7 (cathedral shoulders, OpenSCAD-specific) and RNG-8
> (style registry over OpenSCAD) were deleted — both are superseded by the
> RingSpec + module-library foundation. **RNG-20** (vision spec castable by
> construction) was deleted on 2026-07-20: its premise was disproved — a probe of
> real photos generated 3/3 watertight with zero repairs, so it was solving a
> hypothetical.

## Current Phase

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

**Next:** RNG-18 (clean clone is broken), then RNG-22 (make fidelity measurable),
then RNG-23 (the biggest visual win). RNG-27 can run in parallel.
