# RNG-4: Three.js STL viewer with orbit controls

**Type:** feature
**Ticket:** RNG-4 (Medium, frontend)
**Depends on:** RNG-3 (done) - the page, the `#viewer` placeholder panel, and `static/app.js` which retains the generated STL as `currentBlob` and calls `showSuccess(blob)`.
**Consumes:** RNG-2 `/generate-ring` (binary STL). RNG-1 orientation note: the raw STL has the setting pointing along +X (sideways), so the viewer owns orientation.

## Problem

After generating, the user gets a Download button but no way to *see* the ring
before committing it to a slicer or a caster. There is a scaffolded `#viewer`
panel sitting empty. Without an inline preview, evaluating the shape means
opening the STL in external software every iteration.

When this is done, a user can generate a ring and immediately see it as an
interactive 3D model (orbit, zoom, pan, wireframe), updating on every new
generation. Before this, they had to download the STL and open it elsewhere.

## Approach

A Three.js viewer that renders the STL blob RNG-3 already holds, mounted in the
existing `#viewer` panel. Confirmed decisions:

1. **Three.js vendored locally + import map.** Pin a recent stable `three` (e.g.
   ~0.169) and its addons (`OrbitControls`, `STLLoader`) under `static/vendor/`,
   loaded via `<script type="module">` + an import map in `index.html`. Works
   offline (this is a local OpenSCAD tool); no runtime CDN dependency.
2. **Decoupled via a custom event.** `app.js` dispatches a `ring:generated`
   `CustomEvent` (detail `{ blob }`) inside `showSuccess()` (one added line). A new
   `static/viewer.js` ES module loads Three and listens. `app.js` stays a classic
   `<script>`; the download path is untouched.
3. **Auto-frame + orient upright.** On each load: center the geometry, fit the
   camera to its bounding sphere, and orient so the ring reads naturally (band
   flat, setting up) regardless of the STL's native +X axis.
4. **Tested via pytest structure + browser QA.** No JS toolchain added. WebGL
   behavior verified in real-browser QA.

### Files

| Path | Change |
|------|--------|
| `static/vendor/three/...` | New - pinned `three.module.js` + `OrbitControls.js` + `STLLoader.js` (vendored, version pinned). |
| `static/viewer.js` | New - ES module: scene/camera/renderer/lights/controls; `STLLoader` parses the blob; auto-frame + orient; wireframe toggle; dispose-and-replace on each new STL; listens for `ring:generated`. |
| `templates/index.html` | Modify - add the import map + `<script type="module" src="viewer.js">`; put a `<canvas>`/mount node + a Wireframe toggle button inside `#viewer`; keep `app.js` as the classic script. |
| `static/app.js` | Modify - one line in `showSuccess()`: `document.dispatchEvent(new CustomEvent("ring:generated", { detail: { blob } }))`. Nothing else changes. |
| `static/styles.css` | Modify - size the canvas to fill the viewer panel; responsive. |
| `tests/test_frontend.py` | Modify - add viewer-structure assertions AND update `test_no_js_framework` to allow vendored Three + `viewer.js` (see Constraints). |

`ringcad/*.py`, `scad/`, the backend are unchanged. This is a frontend-only ticket.

## Acceptance Criteria

1. **AC1 - STL renders on success.** When a generation succeeds, the STL is
   rendered as a 3D mesh in a Three.js canvas inside `#viewer`, driven by the
   `ring:generated` event carrying the blob (no second network fetch).
2. **AC2 - OrbitControls.** The model can be orbited, zoomed, and panned with the
   mouse/trackpad (and touch). Controls are damped/usable, not free-spinning.
3. **AC3 - Lighting.** The scene has one ambient light plus two directional lights
   from different directions (so the form reads with shading, not flat).
4. **AC4 - Wireframe toggle.** A labelled button toggles the mesh between solid
   and wireframe. It reflects state (`aria-pressed`) and is keyboard-operable.
5. **AC5 - Updates on new STL.** Generating again replaces the displayed model:
   the previous geometry/material are disposed (no leak), the new mesh is loaded
   and re-framed. No stale model, no accumulation of meshes.
6. **AC6 - Layout.** Form left / viewer right on desktop, stacked on mobile
   (RNG-3 grid). The canvas fills the viewer panel and resizes with it / the
   window without distortion (correct aspect ratio).
7. **AC7 - Download still works.** The RNG-3 Download STL button still appears on
   success and downloads `ring.stl`, unchanged, with the viewer present.
8. **AC8 - Auto-frame + upright.** On each load the model is centered, fully in
   view (fit to bounding sphere), and oriented so the ring presents naturally
   (band flat, setting up) despite the STL's native sideways orientation.
9. **AC9 - Graceful degradation.** If WebGL is unavailable or the STL fails to
   parse, the viewer panel shows a short message instead of crashing, and the
   Download button still works. No uncaught exception breaks the page.
10. **AC10 - Vendored, no runtime CDN.** Three.js and its addons load from
    `static/vendor/` (pinned), not a CDN. The page renders the viewer with no
    external network requests.

## Edge Cases

| Case | Expected behavior |
|------|-------------------|
| First successful generation | Canvas initializes lazily (or on DOM ready) and shows the model |
| Second/third generation | Old mesh disposed + removed; new model shown, re-framed; memory stable |
| WebGL unavailable (old browser / disabled) | Panel shows "3D preview not available in this browser"; download still works (AC9) |
| STL blob fails to parse | Panel shows a parse-error message; no uncaught error (AC9) |
| Window/panel resized | Renderer + camera aspect update; no stretch (AC6) |
| Generation fails (400/503) | Viewer keeps the last successful model (or stays empty on first); RNG-3 error path unchanged |
| Very large/small model | Auto-frame keeps it fully visible (fit to bounds, AC8) |

## Constraints

- **Three.js is a declared-stack library, not a banned framework.** The project
  rule "no JS frameworks, vanilla only" targets app frameworks (React/Vue/etc.);
  the stack explicitly specifies Three.js for the 3D preview. The RNG-3
  `test_no_js_framework` assertion MUST be updated to permit `viewer.js` and the
  vendored `static/vendor/three/*` module (still forbidding react/vue/angular/
  svelte and runtime CDN bundles). Do not add a bundler or a JS app framework.
- **No build step.** ES modules + import map only; vendored files served as
  static assets.
- **Accessibility (WCAG 2.1 AA):** the canvas carries a text alternative
  (`aria-label`/adjacent description); the Wireframe button is a real labelled,
  keyboard-operable control with `aria-pressed`. The 3D canvas itself is a visual
  progressive enhancement, the STL download remains the accessible artifact path.
- **No new backend, no new dependency** (Three is a vendored static asset, not a
  Python package). `static/viewer.js` <= 300 non-blank LOC (hook-enforced).
- **Performance:** viewer init + first render should feel instant relative to the
  20-50s render that precedes it; dispose old GPU resources on replace (AC5).

## Scope Boundaries

**In scope:** the Three.js viewer (render, OrbitControls, lights, wireframe
toggle, update-on-new-STL, auto-frame/orient, resize, graceful WebGL/parse
fallback), vendoring Three, the `ring:generated` wiring, and viewer structure
tests.

**Out of scope (deferred):**
- mesh_valid / mesh_repaired status indicator -> **RNG-5**.
- Photo upload / `/classify-ring` pre-fill -> **RNG-6**.
- Measurement tools, exploded views, materials/PBR/environment maps, screenshot
  export, animation/turntable -> not now.
- Keyboard-driven orbit (mouse/touch only); the download is the non-visual path.

## Success Metrics

- After a successful generation, the ring is visible and interactive in the panel
  with zero extra clicks (functional).
- Re-generating swaps the model with no mesh/GPU-memory accumulation (dispose
  verified in QA).
- Viewer works offline (0 external network requests for Three).
- WCAG 2.1 AA on the new control (wireframe toggle); 0 critical axe violations
  introduced.

## Test Plan

**Automated (pytest, Flask test client - no JS/WebGL), `tests/test_frontend.py`:**
- The page references `static/viewer.js` and the vendored Three module (import map
  present; vendor path served 200).
- `#viewer` contains a canvas/mount node and a Wireframe toggle button (labelled,
  with `aria-pressed`).
- `test_no_js_framework` updated: still 0 react/vue/angular/svelte/CDN-bundle refs,
  but `viewer.js` + vendored `three` are allowed.
- RNG-3 tests still green (form, download, error regions unchanged).

**Browser QA (headless Chrome with a real GL context, e.g. SwiftShader):**
- Generate -> model renders in the canvas; orbit/zoom/pan work (AC2).
- Wireframe toggle flips solid/wireframe and updates `aria-pressed` (AC4).
- Lighting reads as shaded, not flat (AC3); model is centered, framed, upright (AC8).
- Re-generate -> model replaced, no accumulation (AC5); resize -> no distortion (AC6).
- Download still works with the viewer present (AC7).
- Force WebGL off / feed a bad blob -> graceful message, download still works (AC9).
- axe scan: no critical violations from the new control.

## Dependencies

- RNG-3: `#viewer` panel, `showSuccess(blob)` / `currentBlob`, the page + grid.
- RNG-2: the STL bytes (already in hand as a Blob; no new fetch).
- Vendored `three` + `OrbitControls` + `STLLoader` (pinned, committed to `static/vendor/`).

## Design Notes

- **Init:** lazy-init the scene on first `ring:generated` (or on DOMContentLoaded);
  `WebGLRenderer({ antialias: true })` sized to the panel; `PerspectiveCamera`;
  `OrbitControls` with damping; ambient + 2 directional lights.
- **Load:** `new STLLoader().parse(await blob.arrayBuffer())` -> `BufferGeometry`;
  `computeVertexNormals()` if absent; center via bounding box; rotate to upright
  (map the band plane so the setting points +Y); frame camera to bounding sphere.
- **Replace:** dispose old geometry + material, remove old mesh from the scene
  before adding the new one (AC5).
- **Event contract:** `document.addEventListener("ring:generated", e => render(e.detail.blob))`.
  `app.js` adds exactly: `document.dispatchEvent(new CustomEvent("ring:generated", { detail: { blob } }))` in `showSuccess`.
