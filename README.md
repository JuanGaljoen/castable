# Ring CAD

Parametric jewelry-ring generator. Enter ring parameters (or upload a photo),
and the app generates a watertight 3D model in-process with build123d (an
OpenCASCADE B-rep kernel), validates the mesh, previews it in the browser, and
exports a clean STL (and STEP) ready for lost-wax casting. Four ring styles are
supported — **solitaire, halo, trilogy, and side-stone band** — with round or
oval centre stones.

## Features

- **Parametric geometry** — each ring style is a composition of reusable
  build123d modules (`shank`, `seat`, `prong_setting`, `bezel`, `gallery`,
  `accent_seat`, `accent_prong`, …) fused into one watertight manifold; a
  pluggable `StoneOutline` seam makes stone shape (round / oval) orthogonal to
  the modules that follow it.
- **Typed contract (RingSpec)** — requests are validated against a versioned,
  typed RingSpec schema; castability is checked *before* any geometry runs.
- **Casting-ready output** — manufacturing limits (min wall 0.8 mm, min prong tip
  0.7 mm, single watertight body, zero non-manifold edges) are enforced in the
  geometry, not just hinted in the UI.
- **Mesh validation + auto-repair** — every generated STL is checked for
  castability and conservatively repaired (no remeshing) before download. The
  verdict rides back on response headers and a green/red indicator.
- **STL + STEP export** — STL for print/preview, STEP for CAD interchange.
- **3D preview** — Three.js viewer with orbit/zoom/pan and a wireframe toggle.
- **Photo-assisted entry (optional)** — upload a ring photo and Claude vision
  detects the ring style and populates a full, schema-valid RingSpec (archetype,
  dimensions, stone shape, per-field confidence) that pre-fills the form; every
  estimate stays user-overridable, and low-confidence fields are flagged. Works
  without an API key (the feature degrades gracefully to manual entry).

## Screenshots

![Ring CAD app overview](docs/screenshots/app-overview.png)

## Architecture

A `/generate-ring` request, end to end:

```mermaid
sequenceDiagram
    participant U as Browser (app.js)
    participant F as Flask (app.py)
    participant V as validate_spec
    participant G as compose(spec)
    participant M as Mesh gate
    U->>F: POST /generate-ring {archetype, shank, setting, stones, ...}
    F->>V: parse + validate RingSpec
    V-->>F: 400 naming the bad field (if invalid)
    F->>G: build modules, fuse into one solid
    G->>M: tessellate → watertight / manifold check
    M-->>F: mesh stats (X-Mesh-* headers)
    F-->>U: binary STL (or STEP with ?format=step)
    U->>U: Three.js renders it, Download enabled
```

## Stack

| Layer                | Tech                                           |
| -------------------- | ---------------------------------------------- |
| Geometry kernel      | build123d (in-process OpenCASCADE B-rep)       |
| Contract / IR        | RingSpec (Pydantic v2, versioned + typed)      |
| Backend              | Python + Flask (in-process, no subprocess)     |
| Mesh validation      | trimesh (watertight check + auto-repair)       |
| Frontend             | Single HTML page, vanilla JS (no frameworks)   |
| 3D preview           | Three.js + OrbitControls (vendored, no CDN)    |
| Photo classification | Claude vision API (Haiku 4.5)                  |

## Requirements

- **Python 3.11+**
- Python dependencies in `requirements.txt` (build123d, trimesh, Flask, pydantic —
  all pip-installable; no external CAD binary required).

## Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Run

```bash
# Dev server (http://127.0.0.1:5000)
flask --app ringcad.app run
# or:
python app.py
```

Open <http://127.0.0.1:5000>, enter the parameters, click **Generate**, then
preview and download the STL.

> Note: the built-in Flask server is for development only. Use a production WSGI
> server (gunicorn/uWSGI) to deploy.

## Configuration (environment variables)

| Variable            | Default            | Purpose                                                                                                                       |
| ------------------- | ------------------ | ----------------------------------------------------------------------------------------------------------------------------- |
| `ANTHROPIC_API_KEY` | _(unset)_          | Enables photo classification. **Optional** — without it, photo upload returns a graceful "enter parameters manually" message. |
| `CLASSIFY_MODEL`    | `claude-haiku-4-5` | Claude model used for photo classification                                                                                    |

The Anthropic key is read server-side only and is never sent to the browser. To
enable photo classification, add it to a local `.env` file (gitignored) — the app
loads it at startup via `python-dotenv`:

```
ANTHROPIC_API_KEY=sk-ant-...
```

An explicit environment export also works and takes precedence over `.env`:

```
export ANTHROPIC_API_KEY=sk-ant-...
```

## Ring parameters

The shared core (the solitaire's slice of RingSpec):

| Parameter        | Notes                         |
| ---------------- | ----------------------------- |
| `inner_diameter` | Finger size (mm)              |
| `band_width`     | Shank width (mm)              |
| `band_thickness` | Shank thickness (mm, >= 0.8)  |
| `stone_diameter` | Stone seat sizing (mm; the short axis for oval stones) |
| `stone_height`   | Stone height (mm)             |
| `prong_count`    | 4 or 6 only                   |
| `setting_height` | Gallery / setting height (mm) |

Centre stones also take a `shape` (`round` / `oval`) and, for ovals, a
`length_ratio`. Each other archetype adds its own group on top — `halo`
(accent size/count), `trilogy` (side-stone size/ratio), `side_stone`
(accent row + `retention`) — selectable in the form's style dropdown.

Defaults and sane ranges live in `docs/parameter-ranges.md`. The RingSpec contract
(`docs/ringspec/`) validates types and ranges; non-castable specs (e.g. a wall
under 0.8 mm) are rejected with a structured error before geometry runs.

## API

| Endpoint              | Description                                                                                                                                  |
| --------------------- | -------------------------------------------------------------------------------------------------------------------------------------------- |
| `GET /`               | The single-page app                                                                                                                          |
| `GET /health`         | `{"status": "ok"}`                                                                                                                           |
| `POST /generate-ring` | Accepts a structured RingSpec JSON body (`archetype` + its groups) — or, for back-compat, the flat 7 solitaire params with no `archetype` key. Returns a binary STL (`model/stl`) with `X-Mesh-Valid` / `X-Mesh-Repaired` headers. `?format=step` returns STEP (`model/step`). Non-castable or malformed input returns a 400 JSON error naming the field. |
| `POST /classify-ring` | Accepts an image (multipart `image`); returns `{ring_detected, detected_style, note, spec}` where `spec` is a validated RingSpec with per-field confidence, or 503 if no API key is configured |

Example:

```bash
curl -s -D - -o ring.stl -X POST http://127.0.0.1:5000/generate-ring \
  -H "Content-Type: application/json" \
  -d '{"inner_diameter":16.5,"band_width":2.2,"band_thickness":1.9,
       "stone_diameter":6.5,"stone_height":4,"prong_count":6,"setting_height":6}'

# STEP export
curl -s -o ring.step -X POST "http://127.0.0.1:5000/generate-ring?format=step" \
  -H "Content-Type: application/json" -d '{...same body...}'
```

## Tests

```bash
source .venv/bin/activate
pytest -q
```

Geometry tests build real B-rep solids in-process (a few seconds each); photo
classification tests mock the Anthropic client (no key or network required).

## Project layout

```
app.py                  # repo-root entrypoint (create_app)
ringcad/
  app.py                # Flask app factory + routes
  params.py             # request validation (thin view over RingSpec)
  ringspec/             # RingSpec: typed/versioned contract + castability
  geometry/             # build123d module library + archetype compositions + export
  mesh_validator.py     # trimesh validation + auto-repair
  classify.py           # Claude vision ring classification
templates/index.html    # single-page UI
static/                  # app.js, photo.js, viewer.js, styles.css, vendored three
docs/                    # parameter ranges, RingSpec contract, per-ticket specs
tests/                   # pytest suite
```

## Casting requirements (lost-wax)

Hard manufacturing constraints, enforced in geometry:

- Minimum wall thickness **0.8 mm** throughout
- Minimum prong tip diameter **0.7 mm**
- All modules union into a **single watertight manifold**
- Exported STL has **zero non-manifold edges**
- Mesh validated after every generation; auto-repair attempted if not watertight
