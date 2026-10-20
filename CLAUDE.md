# Ring CAD App

Jewelry ring generator working toward one end goal: **upload any ring photo (or
enter parameters) and get a castable 3D model of that ring.** The app turns input
into a structured ring spec, generates a watertight 3D model, validates the mesh,
previews it in the browser, and exports a clean STL (and STEP) ready for lost-wax
casting. Coverage grows toward "any ring" by widening the module vocabulary, not
by adding templates.

## Stack

- **Geometry kernel:** **build123d** (in-process Python, OpenCASCADE B-rep). B-rep
  gives us `shell()` (real 3D wall-thickness enforcement), `fillet`/`sweep`/`loft`,
  curved surfaces, in-kernel geometry introspection, and STEP export.
- **IR / contract:** **RingSpec**: a versioned, typed schema between the vision
  layer and the geometry layer. It's what the user edits and where the
  castability rules validate.
- **Backend:** Python + Flask.
- **Castability gate:** pre-geometry rules on the spec
  (`ringcad/ringspec/castability.py`), in-kernel `check_*` self-checks on the
  B-rep, and Trimesh (watertight check, auto-repair as a fallback only).
- **Frontend:** Single HTML page, vanilla JS only (no frameworks).
- **3D preview:** Three.js with OrbitControls.
- **AI:** Claude API vision: photo -> RingSpec (base dimensions, stone shape,
  shank profile, the set of features present, per-field confidence).

## Architecture (photo -> castable model)

Five layers with one load-bearing artifact (RingSpec) in the middle:

1. **Vision / Understanding:** photo -> RingSpec (Claude vision, `ringcad/classify.py`).
2. **RingSpec (the contract):** versioned, typed; both sides evolve against it
   independently; carries castability validation rules (`ringcad/ringspec/`).
3. **Procedural geometry:** RingSpec -> geometry via a **library of composable
   modules** on build123d (`ringcad/geometry/`: `shank`, `prong_setting`, `seat`,
   `bezel`, `accent_seat`, `accent_prong`, `gallery`, `halo`, `trilogy`,
   `side_stone`, …), each parametric and each emitting castable geometry.
   `compose(spec)` (`assembly.py`) builds the base modules (`shank`, `seat`,
   `prong_setting`) plus one module per feature present. **Connectivity
   standard:** elevated settings (trilogy today, cathedral shoulders when built) attach via the reusable
   `gallery` primitive (the understructure that ties a raised setting to the
   shank/centre for a single watertight manifold); the halo plate hangs off the
   centre claws; side-stone accents are set INTO the band.
4. **Castability gate:** `shell`/thickness, manifold, min-feature checks; much of
   it in-kernel by construction.
5. **Export:** STEP (CAD interchange) + STL (print/preview).

**Core principle:** a ring is a **composition of modules over a shared spec, not
a monolithic template.** Progress toward "any ring" means growing the module
vocabulary and the composition rules, not piling up per-style templates.

## RingSpec

`ringcad/ringspec/models.py`, `version: "1.0"`. A ring is a **base** plus
whichever **features** are present, in any combination:

| Group | Fields |
|---|---|
| `shank` | `inner_diameter` (finger size, mm), `band_width`, `band_thickness` (>= 0.8), `shank_taper` (width flare at the head), `outer_profile` (`domed`/`flat`/`knife_edge`), `inner_profile` (`domed`/`flat`) |
| `setting` | `prong_count` (**4 or 6 only**), `setting_height` |
| `stones` | `stone_diameter` (the **short** axis), `stone_height`, `shape` (`round`/`oval`/`cushion`/`emerald`/`pear`/`marquise`), `length_ratio` (long/short, 1.0-2.5) |
| `halo` (optional) | accent diameter/height/count, `halo_gap` |
| `trilogy` (optional) | side stone diameter/height, `side_stone_gap` |
| `side_stone` (optional) | accent diameter/height, `accent_count_per_side`, `accent_gap`, `retention` (`channel` only) |

Plus `motifs` and `confidence` (per-field, 0-1). Field bounds live on the models.

- **Ratios, not lengths, for shape:** `length_ratio` rather than a stone length,
  because a ratio is what a photo shows. `inner_diameter` is never estimated
  from a photo.
- **The legacy `archetype` tag** (`solitaire`/`halo`/`trilogy`/`side_stone`) is
  still accepted and translated at the `validate_spec` edge; nothing emits it.
- **Coherence:** `make_coherent` (`ringspec/coherence.py`) repairs a
  vision-assembled spec by acting on whichever `Violation` the castability gate
  returns, keyed on its code, not on a restated rule table (docs/adr/0009).
  Bounded at `MAX_PASSES`. Fallback chain: detected features repaired ->
  plain solitaire from the same estimates repaired -> pure defaults.
- **Cross-feature castability:** each feature reports the annular sector it
  occupies (`ringspec/footprint.py`), and one generic pairwise check compares
  them. Placement that depends on another feature (e.g. the side-stone row
  starting further round when a halo shares the head) is derived, and the gate
  and the builder read the same derived value.

## Casting Requirements (lost-wax)

These are hard manufacturing constraints, enforced in geometry, not just UI hints:

- Minimum wall thickness **0.8mm** throughout (for the band, checked at the
  section's centreline; see docs/adr/0011)
- Minimum prong tip diameter **0.7mm**
- All modules must union into a **single watertight manifold**
- Exported STL must have **zero non-manifold edges**
- Mesh validated after every generation; auto-repair attempted if not watertight.
  Generated geometry is watertight by construction, so repair is a safety net,
  not something any archetype relies on.

## Geometry conventions

- **Stone shape is one seam: `StoneOutline`** (`ringcad/geometry/outline.py`).
  It answers `wire()`, `prong_angles()`, `frame_at()`, `half_width()`,
  `min_curvature_radius()`, `expanded()`, `angles_by_arc()`, `tube()`. Round and
  oval have their own classes; every other cut is a `CutProfile` in
  `ringcad/ringspec/cuts.py`, built by the shared `ProfileOutline`. **A new cut is
  a new profile entry, not an edit to the modules that consume it.**
- **Consumers split two ways:** *curve-walkers* (`seat`, `bezel`,
  `prong_setting`, `halo`) take the path and frames; *width-consumers*
  (`trilogy` placement, the overcrowding checks) take a half-width only.
  `c["stone_r"]` survives only for scale-derived values (peg, hub radii), never
  for anything that follows the girdle. When a scalar becomes a shape, audit
  every consumer, gates first (docs/adr/0006).
- **`sections.head_r` is the single source for the band's outer radius at the
  head**, where every setting welds in. Castability, footprint and geometry all
  call it.
- **Model the negative:** we render metal only, so build the body and cut the
  stones out rather than assembling setting parts; assert mesh body count on
  subtractive modules (docs/adr/0008).
- **Fuse leaf solids in one general fuse; join transversally, never graze**
  (docs/adr/0001). **Assert volume, not just watertightness** (docs/adr/0005).
- **Prefer making a bad value unbuildable over a gate rule that rejects it**
  (docs/adr/0012).

## Vocabulary

- **Court:** `domed` outer + `domed` inner, the literal ellipse section; its
  edges taper to zero thickness by design.
- **Comfort fit:** a domed **inner** surface only, paired with any outer shape.
  Not an outer profile.
- **Tapered:** a band that narrows away from the head (`shank_taper`).
  "Graduated" is the trade's term for accent-stone sizing along a band, not a
  band shape.
- **Semi-mount:** a mount with no stones set, which is exactly what we render.
- **Channel:** accents held between two walls cut into the band, with no
  per-stone collar. **Pave:** accents held by raised beads of the band's own
  metal (not yet expressible: `retention` is `channel` only).

## UI Design Specs

- **Layout:** single-view workspace on desktop, **no page scroll**. Sidebar on
  the left (~1/3: photo, then fields two per row, Generate pinned at its
  foot); the 3D viewer fills the right ~2/3 at full height and is the centre
  piece. The viewer owns the result: a header row over the canvas carries the
  title + castability status (left) and one toolbar of secondary-weight
  controls (right): an icon-only Download (aria-label + title "Download")
  LEFT of Wireframe, so Wireframe never shifts when Download appears. Download
  is a menu button: **STL** saves the in-memory blob, **STEP** is rebuilt on
  demand from the request that drew the preview (never the live form), busy +
  announced while it builds, aborted by a new Generate. Generate is the only
  filled button on screen. Base fields must fit at 1440x900 with no inner
  scroll, before AND after a generate; only detected features may push the
  sidebar body into its own scroll. Stacked vertically on mobile (<880px), page
  scrolls there.
- **Form:** base fields with sensible defaults: shank dimensions plus outer and
  inner profile, setting height, `prong_count` as a dropdown limited to 4 or 6,
  stone dimensions plus shape and length ratio. Feature fieldsets (halo,
  trilogy, side-stone) stay hidden until a photo detects that feature, and each
  carries a Remove. The form always posts a structured RingSpec.
- **Actions:** Generate button POSTs JSON to `/generate-ring`; the Download
  button appears on success and keeps working after the viewer is added.
  Generate is disabled (with a hint saying why) while the form would post the
  same request as the last successful generate. This is compared by request
  body, so editing a value back disables it again; a failed run leaves it
  enabled. A loading spinner covers the viewer while a ring generates.
- **Viewer:** Three.js canvas, OrbitControls (orbit/zoom/pan), ambient + two
  directional lights, wireframe toggle button; re-renders on each new STL.
- **Mesh status:** quiet inline text (glyph + colour, no pill) beside the
  "3D preview" heading (proximity: it describes the model), shown **only when
  something is off**: red "Not castable" or "auto-repaired". A clean mesh is
  the norm (watertight by construction), so it shows nothing; the dimensional
  casting rules are enforced earlier, by the spec gate. Download works
  regardless of validation status. Success ("Done — download ready.") is
  announced via a visually hidden live region, not printed; the render and
  the Download button are the visible confirmation. See
  `docs/research/viewer-actions-and-status-ui.md`.
- **Errors:** error message displayed on generation failure. The field marker
  clears as the user types a correction; the banner, which carries the
  instruction being followed ("must be at least 0.8mm"), stays until the next
  submit.
- **Photo flow:** upload (jpg/png) -> `/classify-ring` -> form pre-filled with
  estimates and the detected features shown. Show clear "Estimates only,
  verify before generating" label; every pre-filled field stays
  user-overridable. Fields with confidence < 0.5 get an amber marker + aria
  note; fields the coherence repair moved get a dashed-indigo border + their
  own note (distinct from amber, not colour alone). Fail gracefully on
  blurry/non-ring photos.
- **Feedback lifetime:** feedback about an input must not outlive that input's
  value, and it splits two ways. *Claims about the input* (the photo status
  line, the "Detected: …" line) clear as soon as a different file is chosen.
  *Cautions about values* (amber, indigo) survive until the values change,
  because dropping a caution while its suspect value is still in the form is
  worse than a stale caution. An instruction survives the keystrokes that
  satisfy it; a state indicator dies with the value.
- **Accessibility:** WCAG 2.1 AA mandatory.

## API Endpoints

- `POST /generate-ring`: accepts a structured RingSpec JSON body (keyed on
  `shank`: base groups plus any of `halo`/`trilogy`/`side_stone` ->
  `validate_spec` -> `compose(spec)`), or, for back-compat, the flat 7 solitaire
  params (`inner_diameter`, `band_width`, `band_thickness`, `stone_diameter`,
  `stone_height`, `prong_count`, `setting_height`) with no `shank` key ->
  `from_params` -> `build_solitaire`. The flat body has no stone shape or
  profile, so it always builds a round, court-profile solitaire. Returns binary
  STL on success with `X-Mesh-*` headers; `?format=step` returns STEP
  (`model/step`). Castability violations and malformed input return a 400 JSON
  error naming the field. A mesh that comes out in more than one piece is
  refused with a 400 ("disconnected geometry"), since it cannot be cast; every
  other mesh fault still ships, flagged in `X-Mesh-Valid`. A kernel failure on a spec that passed the gate is a
  500 with a fixed message: the exception is logged, never sent to the client.
  Geometry built in-process via build123d.
- `GET /health`: returns `{"status": "ok"}`.
- `POST /classify-ring`: accepts an image, returns
  `{ring_detected, detected_style, note, spec, adjustments}`: a coherent,
  `validate_spec`-checked RingSpec plus the fields the coherence repair moved.
  Images over 8 MB get a JSON 413; `MAX_CONTENT_LENGTH` refuses an oversized
  request from its `Content-Length` before the body is read, and the handler
  holds the exact 8 MB file limit under it.

## Vision layer

- Default model `claude-haiku-4-5` (`classify.DEFAULT_MODEL`), overridable with
  `CLASSIFY_MODEL`. Low-confidence threshold 0.5 (`static/photo.js`).
- **Every field in the structured-output schema is required, no defaults**; `0`
  is the "not estimated" sentinel the parser reads. Optional fields make the
  real API reject or hang (docs/adr/0004). `tests/test_classify_schema.py`
  guards it offline.
- `.env` loads at startup (`load_dotenv()` in `create_app()`); explicit exports
  win.
- Vision is not deterministic: the same photo can classify differently run to
  run.

## Development & verification

- **Tracker:** Orbit, project **RING** (https://orbit-zeta-gilt.vercel.app). It
  answers "what's next". Frozen designs live in `specs/`, one file per ticket.
  Lessons live in `docs/adr/`.
- **Dependencies:** `build123d`, `cadquery-ocp-novtk` (the OpenCASCADE binding,
  *not* "OCP") and `pydantic` are declared and pinned in `requirements.txt`.
  `tests/test_requirements.py` walks the real AST of `ringcad/` and fails on any
  undeclared or unpinned import.
- **Dev server:** `python wsgi.py`. It runs with **reload off**, so it keeps
  serving pre-edit code. Confirm the process is younger than the edit before
  trusting a before/after (docs/adr/0016).
- **Fidelity probe:** `python probes/fidelity_probe.py` runs the committed photo
  corpus (`probes/corpus/manifest.json`) through the real `/classify-ring` ->
  `/generate-ring` path and saves geometry to `probes/output/` (gitignored).
  One real API call per photo (about 2 cents for the corpus); 15-56s per photo,
  mostly B-rep generation. The failure bar is **generation**: a feature mismatch
  is reported as **amber** (an ambiguous photo must not cry wolf), and a
  manifest entry with no photo is a **gap**, not a failure. Adding a photo is a
  manifest entry plus a file, no code. Its pure core (`load_manifest`,
  `evaluate`) is tested offline; the harness itself is a script pytest never
  collects. Compare geometry or presentation changes from a saved
  `<slug>.spec.json`; re-run the full probe, more than once, when measuring
  vision (`probes/README.md`).
- **Reference sketches:** `docs/reference/` holds trade semi-mount sketches as
  design targets, one per archetype or cut (`docs/reference/README.md` lists
  which exist and which are wanted). Adding one is a file plus a table row.
  Render defects are found by comparing a render against these sketches, not
  by the suite, so get the sketch for whichever archetype or cut you touch.
- **Run the probe before and after fidelity work.**
- **Frontend tests** are Python source inspection (`tests/test_frontend_*.py`).
  They prove a listener is wired, never that it fires; DOM behaviour is proved
  in a browser.
- **Zero-install browser QA:** `playwright` is in the venv, and
  `p.chromium.launch(channel="chrome")` drives the system Chrome against the
  real dev server with no browser download. The script lives outside the repo,
  so `requirements.txt` is untouched. Mutation-test it against the code without
  the fix before trusting it (docs/adr/0017).
- **Run the real path** (probe, upload, render or browser) before calling vision,
  shape or UI work done (docs/adr/0016).

## Rules

- TDD: RED -> GREEN -> REFACTOR. No production code without a failing test.
- Never rewrite working code to fix broken code; fix only the broken module.
- WCAG 2.1 AA mandatory for all UI work.
- No JS frameworks; vanilla only.
- Casting constraints (above) are non-negotiable.
- Never force push.
- A comment explains why the code is this way, never which ticket changed it.
- **Checkpoint archetype builds at module seams.** Build each archetype in
  stages that follow the module-composition boundary (reusable primitive ->
  composition -> API/UI wire-up) and commit at each seam. Every checkpoint
  commit must be trustworthy on its own: tests green, no half-written module.
  A rate-limit interruption or aborted session must always leave the tree at a
  resumable commit, never mid-module. Prefer many small trustworthy commits
  over one large one. Extract genuinely reusable primitives (accent settings,
  pave beads) as their own unit; do not split a single archetype into
  contract/geometry/UI "tickets", which is phase-gating dressed up as scope.
- **The form is a correction surface, not a configurator.** The end goal is
  *upload a ring photo and get a castable model of that ring*. The photo is
  the only thing that puts a FEATURE on a ring. The form's job is to let a
  user fix what vision got wrong (every dimension editable, a Remove on each
  detected feature), never to offer a catalogue of parts to assemble a ring
  from. A feature picker (checkboxes, then an "Add a feature" disclosure) was
  built twice and rejected on sight both times: hand-picking features reads as
  a product configurator, and putting it above the dimensions greets the user
  with style selection before they have uploaded anything. **Adding a control
  is not the same as supporting a capability**: ask whether the photo can
  supply it before putting it in front of anyone.
