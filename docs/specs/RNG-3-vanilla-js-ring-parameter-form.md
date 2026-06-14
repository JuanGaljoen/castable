# RNG-3: Vanilla JS frontend with ring parameter form

**Type:** feature
**Ticket:** RNG-3 (Medium, frontend)
**Depends on:** RNG-2 (done) - `POST /generate-ring`, `GET /health`, Flask app-factory in `ringcad/app.py`
**Blocks:** RNG-4 (Three.js viewer), RNG-6 (photo upload pre-fill)

## Problem

The `/generate-ring` endpoint works, but the only way to drive it is curl. A
jeweller or customer has no way to enter ring parameters and get an STL. There
is also no route in the Flask app that serves a page at all.

When this is done, a user can open the app in a browser, fill in the 7 ring
parameters (with sensible defaults), click Generate, wait for the render, and
download a clean STL. Before this, they had to hand-craft a JSON body and POST
it with curl.

## Approach

A single HTML page served by the existing Flask app, with vanilla JS only (no
frameworks, per the project rule). Confirmed decisions:

1. **Serve via Flask.** Add a `GET /` route to `create_app()` that returns
   `render_template("index.html")`; ship `static/app.js` and `static/styles.css`.
   Uses Flask's default `templates/` and `static/` folders (both already exist).
2. **Soft input bounds.** The 7 inputs are HTML5 number inputs carrying
   `min`/`max`/`step` from `docs/parameter-ranges.md`; `prong_count` is a
   `<select>` limited to 4 and 6. Bounds guide the user; the backend still clamps
   out-of-range by construction as the safety net.
3. **Generate holds a blob; Download button appears.** Generate POSTs JSON via
   `fetch`, shows a loading state during the (20-50s) render, and on success
   keeps the STL `Blob` in memory and reveals a Download STL button that saves it
   as `ring.stl`. Holding the blob lets RNG-4's viewer reuse it.
4. **Tested via Flask HTML-structure tests + browser QA.** No JS toolchain added.

### Files

| Path | Change |
|------|--------|
| `templates/index.html` | New - the single page: parameter form (left), viewer placeholder panel (right), status/error region, download button. |
| `static/app.js` | New - vanilla JS: gather form values, POST to `/generate-ring`, loading state, success (blob + download), error mapping. |
| `static/styles.css` | New - responsive 2-column layout (form left / viewer right; stacked on mobile), accessible focus styles, status/error styling. |
| `ringcad/app.py` | Modify - add `GET /` serving `index.html`. Small, no change to `/generate-ring`. |
| `tests/test_frontend.py` | New - Flask test client asserts served-page structure. |

`ringcad/render.py`, `ringcad/params.py`, `scad/solitaire.scad` unchanged.

### Form defaults and bounds (from docs/parameter-ranges.md)

| Param | Default | min | max | step | Control |
|-------|---------|-----|-----|------|---------|
| `inner_diameter` | 16.5 | 14 | 23 | 0.1 | number |
| `band_width` | 2.2 | 1.6 | 6 | 0.1 | number |
| `band_thickness` | 1.9 | 0.8 | 4 | 0.1 | number |
| `stone_diameter` | 6.5 | 2 | 10 | 0.1 | number |
| `stone_height` | 4 | 2 | 6 | 0.1 | number |
| `prong_count` | 6 | - | - | - | select (4, 6) |
| `setting_height` | 6 | 3 | 8 | 0.1 | number |

## Acceptance Criteria

1. **AC1 - Page served at `/`.** `GET /` returns 200 `text/html` containing the
   ring parameter form. (Currently the app has no `/` route.)
2. **AC2 - Inputs for all 7 params with defaults.** The form has a labelled
   control for each of the 7 params, pre-filled with the defaults above. Each
   number input carries the `min`/`max`/`step` from the table.
3. **AC3 - prong_count is a 4/6 dropdown.** `prong_count` is a `<select>` whose
   only options are `4` and `6`, defaulting to `6`. No free-text entry.
4. **AC4 - Generate POSTs JSON to /generate-ring.** Clicking Generate sends a
   `POST` to `/generate-ring` with `Content-Type: application/json` and a body of
   exactly the 7 params (numbers; `prong_count` an integer). No extra keys.
5. **AC5 - Loading state during render.** While the request is in flight, Generate
   is disabled and a status message indicates work is in progress (renders take
   up to ~1 minute). The status region is `aria-live` so it is announced.
6. **AC6 - Download STL button appears on success.** On a 200 `model/stl`
   response, the STL bytes are kept as a `Blob` and a Download STL button appears
   that saves the file as `ring.stl`. The button keeps working for repeated
   downloads of the same result.
7. **AC7 - Error message on failure.** On any non-200 (400 validation, 400 render
   failure, 503 OpenSCAD-unavailable) or a network error, a visible, `aria-live`
   error message is shown. Validation errors (`{error, detail, field}`) name the
   problem and highlight the offending field; render failures show `error` with
   the `openscad_stderr` available in a collapsible `<details>`. No raw stack
   dumps shown as the primary message.
8. **AC8 - No JS frameworks.** Only vanilla JS; no framework or bundler. (Verified
   by inspection / no framework imports in `static/app.js`.)
9. **AC9 - WCAG 2.1 AA.** Every input has an associated `<label>`; the form is
   keyboard-operable; status and error use `aria-live`; focus moves to the result
   (download) or error region after a submit; colour is not the only error signal;
   text contrast meets AA.

## Edge Cases

| Case | Expected behavior |
|------|-------------------|
| Submit with defaults | Valid POST, render, download button appears |
| A field cleared / non-numeric | HTML5 validation blocks submit and focuses the field (browser-native), before any POST |
| Value outside soft bounds (if forced) | Backend accepts and clamps; UI still shows the STL (bounds are soft) |
| Backend 400 validation `{field}` | Error message shown; named field visually flagged + focused |
| Backend 400 render failure | Error message shown; `openscad_stderr` in a `<details>` |
| Backend 503 (OpenSCAD unavailable) | Clear "ring generator is unavailable" message; no download button |
| Network error / fetch rejects | Friendly "could not reach the server, try again" message |
| Second Generate after a success | Previous download button/blob cleared, fresh loading state, new result |
| Slow render (up to ~120s) | Loading state persists; no premature timeout on the client (let the server own the timeout) |

## Constraints

- **No JS frameworks or build step** - vanilla JS, plain CSS, served as static
  assets. (Project hard rule.)
- **Accessibility: WCAG 2.1 AA** (mandatory; checked in QA / design review).
- **Latency:** the UI must stay responsive and clearly "working" through a 20-50s
  (up to 120s) synchronous render. Do not set a client-side fetch timeout shorter
  than the server's `RENDER_TIMEOUT` (120s).
- **Layout:** responsive - form left / viewer-area right on desktop, stacked on
  mobile. RNG-3 scaffolds the grid with an empty placeholder viewer panel; RNG-4
  fills it with the Three.js canvas. Reusing the held STL `Blob`.
- **Request shape:** send exactly the 7 whitelisted params as JSON; `prong_count`
  as an integer. No unknown keys (the backend rejects them).
- **`static/app.js` <= 300 non-blank LOC** (hook-enforced for .js).

## Scope Boundaries

**In scope:** the served page, the 7-param form with defaults/bounds, the 4/6
dropdown, Generate (POST + loading state), success download button (blob held),
error handling for all backend failure modes, responsive accessible layout, the
`GET /` route, and frontend structure tests.

**Out of scope (deferred):**
- Three.js STL viewer / orbit controls / wireframe toggle -> **RNG-4** (the
  placeholder panel is scaffolded here; the viewer is not).
- Photo upload and `/classify-ring` pre-fill -> **RNG-6**.
- Mesh-valid / mesh-repaired status indicator -> **RNG-5** (no validation flags in
  the RNG-2 response yet).
- Saving/loading parameter presets, share links, unit toggle (mm/inch) -> not now.
- A JS unit-test toolchain (jsdom/vitest) -> not added; interaction verified in QA.

## Success Metrics

- A user can generate and download an STL from the browser with zero curl, in a
  single page load (functional).
- Every backend failure mode (400 validation, 400 render-fail, 503) surfaces a
  human-readable message, not a blank page or raw JSON (0 unhandled responses).
- Axe / manual WCAG 2.1 AA pass on the form (0 critical a11y violations).

## Test Plan

**Automated (pytest, Flask test client - no JS toolchain), in `tests/test_frontend.py`:**
- `GET /` -> 200, `text/html`, body contains the form.
- The page contains a labelled control for each of the 7 params with the correct
  default `value` (assert each name + default).
- `prong_count` is a `<select>` with exactly options 4 and 6.
- Number inputs carry the expected `min`/`max` for at least a representative
  sample (e.g. `band_thickness` min 0.8, `inner_diameter` min 14 max 23).
- The page references `static/app.js` and `static/styles.css`.
- A Download control and an error/status region exist in the markup (hidden by
  default is fine).
- No framework `<script src>` (no react/vue/etc.) - AC8 guard.

**Browser QA (manual/headless in the QA phase, server running):**
- Fill defaults, Generate -> loading state -> Download STL button -> file saves as
  `ring.stl`, loads in a slicer/trimesh.
- Force a backend error (e.g. stop OpenSCAD or craft a 400) -> error message shown,
  field flagged where applicable.
- Keyboard-only walkthrough; screen-reader announcement of status/error;
  axe-core scan for AA.

## Dependencies

- RNG-2: `POST /generate-ring` (binary STL or JSON error), `GET /health`,
  `create_app()` in `ringcad/app.py`.
- `docs/parameter-ranges.md` for defaults and bounds.
- Flask's bundled `templates/` + `static/` handling (no new dependency).

## Design Notes

- **Layout (desktop):** two-column CSS grid - left column the form (`<form>` with
  fieldset/labels, Generate button, status region, Download button, error region);
  right column an empty `#viewer` panel placeholder (RNG-4). Single column stacked
  on narrow viewports.
- **Request:** `fetch("/generate-ring", {method:"POST", headers:{"Content-Type":
  "application/json"}, body: JSON.stringify(params)})`; on `res.ok` read
  `res.blob()`, `URL.createObjectURL`, wire the Download button; else read
  `res.json()` and render the error. Revoke old object URLs on re-generate.
- **prong_count** parsed as `parseInt` so the body carries an integer.
