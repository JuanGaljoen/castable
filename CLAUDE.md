# Ring CAD App

Parametric solitaire ring generator. Users enter ring parameters (or upload a
photo), the app generates a watertight 3D model via OpenSCAD, validates the mesh,
previews it in the browser, and exports a clean STL ready for lost-wax casting.

## Stack

- **Geometry:** OpenSCAD (parametric `.scad` template, headless via CLI)
- **Backend:** Python + Flask, calls OpenSCAD via `subprocess`
- **Mesh validation:** Trimesh (watertight check + auto-repair)
- **Frontend:** Single HTML page, vanilla JS only (no frameworks)
- **3D preview:** Three.js with OrbitControls
- **AI:** Claude API vision for photo-based ring classification

## Casting Requirements (lost-wax)

These are hard manufacturing constraints, enforced in geometry, not just UI hints:

- Minimum wall thickness **0.8mm** throughout
- Minimum prong tip diameter **0.7mm**
- All modules must union into a **single watertight manifold**
- Exported STL must have **zero non-manifold edges**
- Mesh validated after every generation; auto-repair attempted if not watertight

## Ring Parameters (7)

| Parameter        | Notes                          |
|------------------|--------------------------------|
| `inner_diameter` | Finger size (mm)               |
| `band_width`     | Shank width (mm)               |
| `band_thickness` | Shank thickness (mm, >= 0.8)   |
| `stone_diameter` | Stone seat sizing (mm)         |
| `stone_height`   | Stone height (mm)              |
| `prong_count`    | **4 or 6 only** (dropdown)     |
| `setting_height` | Gallery/setting height (mm)    |

OpenSCAD modules: `shank()`, `gallery()`, `prongs()`, `seat()` -> unioned.

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

- `POST /generate-ring` - accepts all 7 params as JSON, returns binary STL on
  success, OpenSCAD stderr + 400 on failure. Handles missing/invalid params.
- `GET /health` - returns `{"status": "ok"}`.
- `POST /classify-ring` - accepts an image, returns Claude vision estimates
  (style, prong count, shank taper, features) + estimated dimensions.

## Commands

Workspace pipeline commands (see `~/projects/personal/.claude/CLAUDE.md`):

- `/plan-feature`   - interactive planning, produces a spec file
- `/build-feature`  - full TDD pipeline with review, reflect, persist
- `/review-impl`    - standalone five-pillar code review
- `/ship`           - branch, commit, push, PR
- `/audit-security` - OWASP Top 10 audit
- `/freeze`         - lock scope to specific files

## Rules

- TDD: RED -> GREEN -> REFACTOR. No production code without a failing test.
- Never rewrite working code to fix broken code; fix only the broken module.
- Max 300 LOC per file; split if larger.
- Zero `console.log` in committed code.
- WCAG 2.1 AA mandatory for all UI work.
- No JS frameworks; vanilla only.
- Casting constraints (above) are non-negotiable.
- Never force push.

## Tickets (Jira project: RNG)

Dependency-ordered (`Blocks` links in Jira):

- **RNG-1** OpenSCAD parametric solitaire ring template [foundation, Highest]
- **RNG-2** Flask backend with STL generation endpoint [backend, Highest] - needs RNG-1
- **RNG-3** Vanilla JS frontend with ring parameter form [frontend, Medium] - needs RNG-2
- **RNG-4** Three.js STL viewer with orbit controls [frontend, Medium] - needs RNG-3
- **RNG-5** Trimesh mesh validation and auto-repair [backend, Medium] - needs RNG-2
- **RNG-6** Photo upload with Claude vision ring classification [backend, frontend, Low] - needs RNG-3

## Current Phase

**RNG-1 - OpenSCAD parametric solitaire ring template.**

Build the parametric `.scad` template. Acceptance criteria:

- Separate modules: `shank()`, `gallery()`, `prongs()`, `seat()`
- All 7 parameters wired through
- Min wall thickness 0.8mm and min prong tip 0.7mm enforced throughout
- All modules union into a single watertight manifold
- Geometry updates correctly when any parameter changes
- Exports clean STL with zero non-manifold edges
