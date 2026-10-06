"""Frontend structure tests for the served ring parameter page (RNG-3).

TDD RED: these tests define the static HTML the Flask app must serve at
`GET /`. Today the app has NO `/` route (only /health + /generate-ring), so
`GET /` returns 404 and every structure assertion fails -> correct RED signal.
The implementer lands the `GET /` route + templates/index.html to turn these
GREEN.

SCOPE: these tests assert the served HTML STRUCTURE only. The Flask test client
runs NO JavaScript, so behavioral ACs (AC4 POST shape, AC5 loading state, AC6
blob/download, AC7 error rendering, AC9 runtime focus/keyboard/contrast) are
verified in the browser QA phase, NOT here. We only assert the static shell
(elements/regions/attributes) that the JS will later drive.

Element ids/names are the authoritative contract from .claude/logs/active_plan.md
and spec.md "## Autonomous Assumptions".
"""
import re

import pytest

from ringcad.app import create_app

# The 7 form keys. Six are number inputs; prong_count is a <select>.
NUMBER_KEYS = [
    "inner_diameter",
    "band_width",
    "band_thickness",
    "stone_diameter",
    "stone_height",
    "setting_height",
]
ALL_KEYS = NUMBER_KEYS + ["prong_count"]

# Defaults from docs/parameter-ranges.md (spec AC2). prong_count default (6)
# is asserted via the <select> option in its own test.
NUMBER_DEFAULTS = {
    "inner_diameter": "16.5",
    "band_width": "2.2",
    "band_thickness": "1.9",
    "stone_diameter": "6.5",
    "stone_height": "4",
    "setting_height": "6",
}


@pytest.fixture
def client():
    app = create_app()
    app.config["TESTING"] = True
    return app.test_client()


@pytest.fixture
def body(client):
    """The served HTML at GET /. Today this 404s (no `/` route) -> RED."""
    resp = client.get("/")
    assert resp.status_code == 200, (
        f"GET / returned {resp.status_code}, expected 200 (no `/` route yet?)"
    )
    return resp.get_data(as_text=True)


def _input_tag_with(html: str, **attrs) -> bool:
    """True if some <input ...> tag carries every name=value attr (any order).

    Tolerant of attribute ordering: matches a single <input> tag whose text
    contains each `name="value"` pair. Avoids brittle exact-string matching.
    """
    for tag in re.findall(r"<input\b[^>]*>", html, re.IGNORECASE):
        if all(
            re.search(rf'{re.escape(k)}\s*=\s*"{re.escape(v)}"', tag, re.IGNORECASE)
            for k, v in attrs.items()
        ):
            return True
    return False


def _select_block(html: str, select_id: str) -> str:
    """Return the <select id=...>...</select> block, or '' if absent."""
    m = re.search(
        rf'<select\b[^>]*id\s*=\s*"{re.escape(select_id)}"[^>]*>(.*?)</select>',
        html,
        re.IGNORECASE | re.DOTALL,
    )
    return m.group(0) if m else ""


# ---- AC1: page served at / ------------------------------------------------
def test_root_returns_html(client):
    resp = client.get("/")
    assert resp.status_code == 200
    assert resp.headers["Content-Type"].startswith("text/html")
    body = resp.get_data(as_text=True)
    assert 'id="ring-form"' in body


# ---- AC2: all 7 inputs present with defaults -------------------------------
def test_all_seven_inputs_present_with_defaults(body):
    for key in ALL_KEYS:
        assert f'name="{key}"' in body, f"missing control name={key}"
    for key, default in NUMBER_DEFAULTS.items():
        assert _input_tag_with(body, name=key, value=default), (
            f"input name={key} missing default value={default}"
        )


# ---- AC2: number input bounds (representative sample) ----------------------
def test_number_input_bounds(body):
    assert _input_tag_with(body, name="inner_diameter", min="14", max="23"), (
        "inner_diameter must carry min=14 max=23"
    )
    assert _input_tag_with(body, name="band_thickness", min="0.8"), (
        "band_thickness must carry min=0.8 (casting floor)"
    )
    # at least one number input declares step=0.1
    assert any(
        _input_tag_with(body, name=key, step="0.1") for key in NUMBER_KEYS
    ), "no number input declared step=0.1"


# ---- AC3: prong_count is a <select> of exactly 4 and 6 (6 selected) --------
def test_prong_count_is_select_4_and_6(body):
    block = _select_block(body, "prong_count")
    assert block, "no <select id=prong_count> found"
    assert re.search(r'name\s*=\s*"prong_count"', block, re.IGNORECASE), (
        "prong_count <select> must carry name=prong_count"
    )
    assert re.search(r'<option\b[^>]*value\s*=\s*"4"', block, re.IGNORECASE)
    assert re.search(r'<option\b[^>]*value\s*=\s*"6"', block, re.IGNORECASE)
    # option value=6 is the selected default
    opt6 = re.search(
        r'<option\b[^>]*value\s*=\s*"6"[^>]*>', block, re.IGNORECASE
    )
    assert opt6 and "selected" in opt6.group(0).lower(), (
        "option value=6 must be selected by default"
    )
    # prong_count must NOT be a free-text input
    assert not _input_tag_with(body, name="prong_count"), (
        "prong_count must be a <select>, not an <input>"
    )


# ---- AC8 wiring: static assets referenced ----------------------------------
def test_static_assets_referenced(body):
    assert "/static/app.js" in body, "page must reference /static/app.js"
    assert "/static/styles.css" in body, "page must reference /static/styles.css"


# ---- AC5/AC6/AC7 shells: result regions present ----------------------------
def test_result_regions_present(body):
    for region_id in ("status", "error", "download-btn", "viewer"):
        assert f'id="{region_id}"' in body, f"missing region id={region_id}"


def test_no_openscad_error_handling_left(body):
    """The OpenSCAD backend is gone, so the server never sends its errors (a
    render failure with stderr, a timeout, a 503 for a missing binary). UI for
    them is dead code a reader has to work out is dead."""
    import pathlib

    app_js = (
        pathlib.Path(__file__).parent.parent / "static" / "app.js"
    ).read_text()
    for remnant in ("stderr", "OpenSCAD", "Render timed out", "503"):
        assert remnant not in app_js, f"app.js still handles {remnant!r}"
    assert 'id="stderr-details"' not in body


# ---- AC9 structural: aria-live regions -------------------------------------
def test_aria_live_regions(body):
    status = re.search(r'<[^>]*id\s*=\s*"status"[^>]*>', body, re.IGNORECASE)
    assert status, "no element with id=status"
    assert re.search(
        r'aria-live\s*=\s*"polite"', status.group(0), re.IGNORECASE
    ), "#status must carry aria-live=polite"

    error = re.search(r'<[^>]*id\s*=\s*"error"[^>]*>', body, re.IGNORECASE)
    assert error, "no element with id=error"
    err_tag = error.group(0)
    assert re.search(
        r'aria-live\s*=\s*"assertive"', err_tag, re.IGNORECASE
    ) or re.search(r'role\s*=\s*"alert"', err_tag, re.IGNORECASE), (
        "#error must carry aria-live=assertive or role=alert"
    )


# ---- AC9 structural: every input has a matching label[for] ------------------
def test_every_input_has_label_for(body):
    for key in ALL_KEYS:
        assert f'id="{key}"' in body, f"control id={key} missing"
        assert re.search(
            rf'<label\b[^>]*for\s*=\s*"{re.escape(key)}"', body, re.IGNORECASE
        ), f"no <label for={key}>"


# ---- AC8/AC10: no JS framework / CDN bundle; only local first-party + vendor
def test_no_js_framework(body):
    """All script srcs must be first-party (app.js / viewer.js) or locally
    vendored three; the inline import map must point only at /static/ URLs.

    Rewritten for RNG-4: app.js is no longer the *only* script src — viewer.js
    (ES module) and the vendored three files are also referenced. The rule is
    no framework/CDN, all local. Tolerant of attribute ordering.
    """
    forbidden = ("react", "vue", "angular", "svelte", "cdn", "unpkg", "jsdelivr")

    srcs = re.findall(
        r'<script\b[^>]*\bsrc\s*=\s*"([^"]*)"', body, re.IGNORECASE
    )
    assert srcs, "no <script src> at all (expected at least app.js + viewer.js)"
    for src in srcs:
        low = src.lower()
        assert not any(tok in low for tok in forbidden), (
            f"forbidden framework/CDN script src: {src}"
        )
        allowed = (
            low.endswith("app.js")
            or low.endswith("viewer.js")
            or low.endswith("photo.js")
            or "/static/vendor/three/" in low
        )
        assert allowed, (
            f"unexpected script src (not app.js/viewer.js/vendored three): {src}"
        )

    # The inline import map must reference only local /static/ URLs.
    im = re.search(
        r'<script\b[^>]*type\s*=\s*"importmap"[^>]*>(.*?)</script>',
        body,
        re.IGNORECASE | re.DOTALL,
    )
    assert im, "no inline <script type=importmap> found"
    import_urls = re.findall(r'"([^"]*)"\s*:\s*"([^"]*)"', im.group(1))
    mapped = [target for _, target in import_urls if "/" in target or "." in target]
    assert mapped, "import map declares no target URLs"
    for url in mapped:
        low = url.lower()
        assert low.startswith("/static/"), (
            f"import map target must be /static/-local: {url}"
        )
        assert not any(
            tok in low for tok in ("cdn", "unpkg", "jsdelivr", "http")
        ), f"forbidden CDN/remote import map target: {url}"


# ---- RNG-4 AC4/AC1/AC9 shell: viewer markup --------------------------------
def test_viewer_structure(body):
    """The #viewer region must expose the canvas, wireframe toggle, and message
    placeholder the viewer JS drives — with their accessibility attributes."""
    canvas = re.search(
        r'<canvas\b[^>]*id\s*=\s*"viewer-canvas"[^>]*>', body, re.IGNORECASE
    )
    assert canvas, "no <canvas id=viewer-canvas>"
    assert re.search(r"aria-label\s*=", canvas.group(0), re.IGNORECASE), (
        "#viewer-canvas must carry an aria-label"
    )

    toggle = re.search(
        r'<button\b[^>]*id\s*=\s*"wireframe-toggle"[^>]*>', body, re.IGNORECASE
    )
    assert toggle, "no <button id=wireframe-toggle>"
    assert re.search(r"aria-pressed\s*=", toggle.group(0), re.IGNORECASE), (
        "#wireframe-toggle must carry aria-pressed"
    )

    assert 'id="viewer-message"' in body, "missing element id=viewer-message"


# ---- RNG-4 AC1 wiring: viewer ES module referenced -------------------------
def test_viewer_module_script(body):
    module_scripts = re.findall(
        r'<script\b[^>]*type\s*=\s*"module"[^>]*>', body, re.IGNORECASE
    )
    assert any("viewer.js" in tag for tag in module_scripts), (
        "no <script type=module> referencing viewer.js"
    )


# ---- RNG-4 AC10 static: import map maps three specifiers to local vendor ----
def test_import_map_specifiers(body):
    im = re.search(
        r'<script\b[^>]*type\s*=\s*"importmap"[^>]*>(.*?)</script>',
        body,
        re.IGNORECASE | re.DOTALL,
    )
    assert im, "no inline <script type=importmap> found"
    block = im.group(1)
    assert re.search(
        r'"three"\s*:\s*"/static/vendor/three/three\.module\.js"',
        block,
    ), '"three" must map to /static/vendor/three/three.module.js'
    assert re.search(
        r'"three/addons/"\s*:\s*"/static/vendor/three/addons/"',
        block,
    ), '"three/addons/" must map to /static/vendor/three/addons/'


# ---- RNG-5 AC4 structural: mesh-status indicator above the download button -
def test_mesh_status_above_download(body):
    """The #mesh-status indicator must exist as a live region and sit ABOVE
    #download-btn in source order.

    SCOPE: static shell only. The header-driven green/red rendering and the
    'download still works when mesh is invalid' behavior are JS-runtime
    concerns verified in the browser-QA phase, NOT here (no JS runs in the
    Flask test client).
    """
    status = re.search(r'<[^>]*id\s*=\s*"mesh-status"[^>]*>', body, re.IGNORECASE)
    assert status, "no element with id=mesh-status"
    tag = status.group(0)
    assert re.search(r'role\s*=\s*"status"', tag, re.IGNORECASE), (
        "#mesh-status must carry role=status"
    )
    assert re.search(r'aria-live\s*=\s*"polite"', tag, re.IGNORECASE), (
        "#mesh-status must carry aria-live=polite"
    )
    # source order: mesh-status appears before the download button
    assert body.index('id="mesh-status"') < body.index('id="download-btn"'), (
        "#mesh-status must appear ABOVE #download-btn"
    )


# ===========================================================================
# RNG-9 CP4: archetype selector + halo fields (archetype-driven visibility)
# ===========================================================================
HALO_NUMBER_KEYS = [
    "halo_stone_diameter",
    "halo_stone_count",
    "halo_gap",
    "halo_stone_height",
]
HALO_DEFAULTS = {
    "halo_stone_diameter": "1.3",
    "halo_stone_count": "14",
    "halo_gap": "0.5",
    "halo_stone_height": "1.2",
}


def test_the_form_never_offers_to_add_a_feature(body):
    """RNG-24: the photo is the only thing that puts a feature on the ring.

    No archetype select, no feature toggles, no "add a feature" control --
    this reproduces a ring you photographed, it does not offer you parts to
    assemble one from. A feature can still be REMOVED (vision is not always
    right); that asymmetry is the design, not an oversight.
    """
    assert not re.search(r'<select\b[^>]*id\s*=\s*"archetype"', body, re.I), (
        "the archetype selector should be gone -- features are composable now"
    )
    assert "add-feature" not in body, (
        "nothing in the form may offer to add a feature"
    )
    for feature in ("halo", "trilogy", "side_stone"):
        assert not _input_tag_with(body, type="checkbox", id=f"feature-{feature}"), (
            f"no feature toggle for {feature} may appear in the form"
        )


def test_each_feature_fieldset_can_be_removed(body):
    """Anything you can add, you can take off again -- with an accessible
    name, since three buttons all reading "Remove" are useless to a screen
    reader (WCAG 2.1 AA)."""
    for feature in ("halo", "trilogy", "side_stone"):
        button = re.search(
            rf'<button\b[^>]*class\s*=\s*"remove-feature"[^>]*'
            rf'data-feature\s*=\s*"{feature}"[^>]*>',
            body,
            re.I,
        )
        assert button, f"no remove control for {feature}"
        assert re.search(r'aria-label\s*=\s*"[^"]+"', button.group(0), re.I), (
            f"the {feature} remove button needs a distinguishing aria-label"
        )


def test_halo_fields_present_with_defaults_and_hidden_by_default(body):
    for key in HALO_NUMBER_KEYS:
        assert f'name="{key}"' in body, f"missing control name={key}"
    for key, default in HALO_DEFAULTS.items():
        assert _input_tag_with(body, name=key, value=default), (
            f"input name={key} missing default value={default}"
        )
    container = re.search(
        r'<fieldset\b[^>]*id\s*=\s*"halo-fields"[^>]*>', body, re.IGNORECASE
    )
    assert container, "no <fieldset id=halo-fields>"
    assert "hidden" in container.group(0).lower(), (
        "#halo-fields must be hidden by default (solitaire is the default archetype)"
    )


def test_halo_fields_have_labels(body):
    for key in HALO_NUMBER_KEYS:
        assert f'id="{key}"' in body, f"control id={key} missing"
        assert re.search(
            rf'<label\b[^>]*for\s*=\s*"{re.escape(key)}"', body, re.IGNORECASE
        ), f"no <label for={key}>"


# ===========================================================================
# RNG-10 CP3: trilogy option + trilogy fields (archetype-driven visibility)
# ===========================================================================
TRILOGY_NUMBER_KEYS = [
    "side_stone_diameter",
    "side_stone_height",
    "side_stone_gap",
]
TRILOGY_DEFAULTS = {
    "side_stone_diameter": "2.5",
    "side_stone_height": "1.8",
    "side_stone_gap": "0.6",
}


def test_trilogy_fields_present_with_defaults_and_hidden_by_default(body):
    for key in TRILOGY_NUMBER_KEYS:
        assert f'name="{key}"' in body, f"missing control name={key}"
    for key, default in TRILOGY_DEFAULTS.items():
        assert _input_tag_with(body, name=key, value=default), (
            f"input name={key} missing default value={default}"
        )
    container = re.search(
        r'<fieldset\b[^>]*id\s*=\s*"trilogy-fields"[^>]*>', body, re.IGNORECASE
    )
    assert container, "no <fieldset id=trilogy-fields>"
    assert "hidden" in container.group(0).lower(), (
        "#trilogy-fields must be hidden by default (solitaire is the default)"
    )


def test_trilogy_fields_have_labels(body):
    for key in TRILOGY_NUMBER_KEYS:
        assert f'id="{key}"' in body, f"control id={key} missing"
        assert re.search(
            rf'<label\b[^>]*for\s*=\s*"{re.escape(key)}"', body, re.IGNORECASE
        ), f"no <label for={key}>"


# ===========================================================================
# RNG-11 CP3: side-stone option + side-stone fields + retention control
# ===========================================================================
SIDE_STONE_NUMBER_KEYS = [
    "accent_stone_diameter",
    "accent_stone_height",
    "accent_gap",
]
SIDE_STONE_INT_KEYS = ["accent_count_per_side"]
SIDE_STONE_DEFAULTS = {
    "accent_stone_diameter": "1.5",
    "accent_stone_height": "1.2",
    "accent_count_per_side": "3",
    "accent_gap": "0.3",
}


def test_side_stone_fields_present_with_defaults_and_hidden_by_default(body):
    for key in SIDE_STONE_NUMBER_KEYS + SIDE_STONE_INT_KEYS:
        assert f'name="{key}"' in body, f"missing control name={key}"
    for key, default in SIDE_STONE_DEFAULTS.items():
        assert _input_tag_with(body, name=key, value=default), (
            f"input name={key} missing default value={default}"
        )
    container = re.search(
        r'<fieldset\b[^>]*id\s*=\s*"side-stone-fields"[^>]*>', body, re.IGNORECASE
    )
    assert container, "no <fieldset id=side-stone-fields>"
    assert "hidden" in container.group(0).lower(), (
        "#side-stone-fields must be hidden by default (solitaire is the default)"
    )


def test_side_stone_fields_have_labels(body):
    for key in SIDE_STONE_NUMBER_KEYS + SIDE_STONE_INT_KEYS:
        assert f'id="{key}"' in body, f"control id={key} missing"
        assert re.search(
            rf'<label\b[^>]*for\s*=\s*"{re.escape(key)}"', body, re.IGNORECASE
        ), f"no <label for={key}>"


def test_side_stone_count_is_int_bounded(body):
    """accent_count_per_side is an integer input bounded to its 1..8 range."""
    assert _input_tag_with(
        body, name="accent_count_per_side", min="1", max="8", step="1"
    ), "accent_count_per_side must be an integer input with min=1 max=8 step=1"


def test_side_stone_retention_control_present_and_labelled(body):
    """The retention control (v1: channel only) is a labelled <select> whose
    single option is `channel`, inside #side-stone-fields."""
    block = _select_block(body, "retention")
    assert block, "no <select id=retention> found"
    assert re.search(r'name\s*=\s*"retention"', block, re.IGNORECASE), (
        "retention <select> must carry name=retention"
    )
    opt = re.search(
        r'<option\b[^>]*value\s*=\s*"channel"[^>]*>', block, re.IGNORECASE
    )
    assert opt, "retention must offer <option value=channel>"
    assert "selected" in opt.group(0).lower(), (
        "option value=channel must be selected by default"
    )
    assert re.search(
        r'<label\b[^>]*for\s*=\s*"retention"', body, re.IGNORECASE
    ), "no <label for=retention>"


# ---- RNG-4 AC10 static: vendored three files are actually served -----------
def test_vendored_three_served(client):
    for path in (
        "/static/vendor/three/three.module.js",
        "/static/vendor/three/addons/controls/OrbitControls.js",
        "/static/vendor/three/addons/loaders/STLLoader.js",
    ):
        resp = client.get(path)
        assert resp.status_code == 200, (
            f"vendored three file not served (got {resp.status_code}): {path}"
        )


# ===========================================================================
# RNG-24: the form's features and app.js's registry must agree
# ===========================================================================
def test_every_feature_fieldset_is_known_to_the_registry(body):
    """A fieldset the registry does not know about is dead markup: the photo
    could detect that feature and nothing would appear, and its values would
    never be sent. The two lists are written in different files, so pin them
    against each other rather than trusting they were updated together."""
    import pathlib

    app_js = (
        pathlib.Path(__file__).parent.parent / "static" / "app.js"
    ).read_text()
    registry = re.search(r"const FEATURES = \{.*?\n\};", app_js, re.S)
    assert registry, "no FEATURES registry in app.js"
    registered = set(re.findall(r"^  (\w+):", registry.group(0), re.M))

    in_form = set(re.findall(r'class="remove-feature"[^>]*data-feature="(\w+)"', body))
    assert in_form, "no feature fieldsets found in the form"
    assert in_form <= registered, (
        f"form offers features app.js does not know: {sorted(in_form - registered)}"
    )
    assert registered <= in_form, (
        f"registry knows features the form never shows: {sorted(registered - in_form)}"
    )


# ---- Download lives on the viewer, not in the sidebar footer --------------
def test_download_button_sits_in_the_viewer(body):
    """#download-btn belongs to the 3D preview (a small control in its top
    right), not the config form: the file it saves is the model on screen.

    SCOPE: static shell only; the corner placement is CSS, checked in a browser.
    """
    viewer = re.search(r'<section[^>]*id="viewer".*?</section>', body, re.S)
    form = re.search(r"<form\b.*?</form>", body, re.S)
    assert viewer and form
    assert 'id="download-btn"' in viewer.group(0), (
        "#download-btn must be inside the #viewer section"
    )
    assert 'id="download-btn"' not in form.group(0), (
        "#download-btn must not remain in the sidebar form"
    )


# ---- Viewer owns its result: status chip + one toolbar (docs/research/
# viewer-actions-and-status-ui.md) -----------------------------------------
def _viewer(body):
    viewer = re.search(r'<section[^>]*id="viewer".*?</section>', body, re.S)
    assert viewer, "no #viewer section"
    return viewer.group(0)


def test_mesh_status_describes_the_model_so_it_sits_in_the_viewer(body):
    """The castability chip describes the rendered model, so it lives beside
    it (NN/g: indicators in close proximity to what they describe)."""
    assert 'id="mesh-status"' in _viewer(body)


def test_wireframe_and_download_share_one_viewer_toolbar(body):
    """Viewer controls are one group, not two stray buttons in two corners."""
    # Up to the canvas, not the first </div>: the download menu nests a div.
    toolbar = re.search(
        r'<div[^>]*class="viewer-toolbar"[^>]*>.*?<canvas', _viewer(body), re.S
    )
    assert toolbar, "no .viewer-toolbar in #viewer"
    assert 'id="wireframe-toggle"' in toolbar.group(0)
    assert 'id="download-btn"' in toolbar.group(0)


def test_success_is_announced_but_not_printed(body):
    """'Done — download ready' is redundant on screen once the model renders
    and Download appears, but screen readers still need it (WCAG 4.1.3): it
    goes to a visually hidden live region, not the visible #status line."""
    tag = re.search(r'<[^>]*id="generate-announce"[^>]*>', body)
    assert tag, "no #generate-announce live region"
    assert "visually-hidden" in tag.group(0)
    assert 'aria-live="polite"' in tag.group(0)
    js = open("static/app.js", encoding="utf-8").read()
    fn = re.search(r"function showSuccess\(blob\)\s*\{.*?\n\}", js, re.S).group(0)
    assert "announceEl.textContent" in fn
    assert "statusEl.textContent = \"Done" not in fn


# ---- Generate is disabled until the geometry changes ----------------------
# SCOPE: wiring only (the Flask client runs no JS); that the button actually
# disables and re-enables is checked in a browser.
def _js(name):
    return open(f"static/{name}", encoding="utf-8").read()


def test_generate_explains_why_it_is_disabled(body):
    """A disabled button that says nothing reads as broken: the hint names
    what re-enables it, and the button points at it."""
    btn = re.search(r'<button[^>]*id="generate-btn"[^>]*>', body).group(0)
    assert 'aria-describedby="generate-hint"' in btn
    hint = re.search(r'<[^>]*id="generate-hint"[^>]*>', body)
    assert hint and "hidden" in hint.group(0)


def test_generate_compares_the_request_not_keystrokes():
    """'Changed' means the request would differ from the last successful one,
    so editing a value back disables Generate again."""
    js = _js("app.js")
    assert "lastGeneratedBody" in js
    sync = re.search(r"function syncGenerateEnabled\(\)\s*\{.*?\n\}", js, re.S)
    assert sync and "JSON.stringify(gatherRequestBody())" in sync.group(0)
    for evt in ('form.addEventListener("input", syncGenerateEnabled)',
                'form.addEventListener("change", syncGenerateEnabled)'):
        assert evt in js, f"missing: {evt}"


def test_photo_estimate_reenables_generate():
    """applySpec assigns .value silently (no input events), so it announces
    when it's done and app.js re-checks."""
    assert 'new CustomEvent("ring:spec-applied")' in _js("photo.js")
    assert 'addEventListener("ring:spec-applied", syncGenerateEnabled)' in _js("app.js")


# ---- Download is an icon button that doesn't shove Wireframe ---------------
def test_download_is_an_icon_button_with_an_accessible_name(body):
    """Icon-only, so the name lives in aria-label (plus a native title
    tooltip for sighted mouse users); the svg itself is decorative. It opens
    a format menu (RNG-48), so the name is the action, not one format."""
    btn = re.search(r'<button[^>]*id="download-btn".*?</button>', body, re.S).group(0)
    assert 'aria-label="Download"' in btn
    assert 'title="Download"' in btn
    assert re.search(r'<svg[^>]*aria-hidden="true"', btn)


# ---- RNG-48: Download opens a format menu (STL / STEP) ---------------------
def _download_menu(body):
    menu = re.search(
        r'<div[^>]*class="download-menu"[^>]*>.*?</ul>\s*</div>', body, re.S
    )
    assert menu, "no .download-menu wrapper"
    return menu.group(0)


def test_download_is_a_menu_button(body):
    """WAI-ARIA menu button: the trigger says it has a menu, whether it is
    open, and which element the menu is."""
    btn = re.search(r'<button[^>]*id="download-btn"[^>]*>', body).group(0)
    assert 'aria-haspopup="menu"' in btn
    assert 'aria-expanded="false"' in btn
    assert 'aria-controls="download-options"' in btn


def test_download_menu_offers_stl_and_step(body):
    menu = _download_menu(body)
    assert re.search(r'<ul[^>]*id="download-options"[^>]*role="menu"', menu)
    assert re.search(r'<ul[^>]*id="download-options"[^>]*hidden', menu), (
        "the menu starts closed"
    )
    items = re.findall(r'<button[^>]*role="menuitem"[^>]*data-format="(\w+)"', menu)
    assert items == ["stl", "step"]


def test_download_menu_hidden_until_a_ring_exists(body):
    """The wrapper, not the button, carries hidden: one attribute to flip."""
    assert re.search(r'<div[^>]*class="download-menu"[^>]*\bhidden\b', body)


def test_step_rebuilds_the_ring_on_screen_not_the_form():
    """STEP is built on demand from the request that drew the preview.
    Reading the form instead would ship a different ring once it has moved
    on (the RNG-30 staleness family)."""
    js = _js("app.js")
    fn = re.search(r"async function downloadStep\(\)\s*\{.*?\n\}", js, re.S)
    assert fn, "no downloadStep()"
    fn = fn.group(0)
    assert "/generate-ring?format=step" in fn
    assert "body: lastGeneratedBody" in fn
    assert "gatherRequestBody" not in fn
    assert 'download = "ring.step"' in fn or "\"ring.step\"" in fn


def test_stl_download_needs_no_request():
    js = _js("app.js")
    fn = re.search(r"function downloadStl\(\)\s*\{.*?\n\}", js, re.S)
    assert fn, "no downloadStl()"
    assert "fetch(" not in fn.group(0)
    assert "currentObjectUrl" in fn.group(0)


def test_new_generate_aborts_an_in_flight_step():
    """clearResult runs on every Generate; a STEP for the old ring must never
    land after the preview has changed."""
    js = _js("app.js")
    fn = re.search(r"function clearResult\(\)\s*\{.*?\n\}", js, re.S).group(0)
    assert "stepController.abort()" in fn


def test_download_appears_left_of_wireframe_so_nothing_shifts(body):
    """Download is hidden until a success; if it sat at the trailing edge,
    Wireframe would jump sideways when it appeared."""
    assert body.index('id="download-btn"') < body.index('id="wireframe-toggle"')


# ---- Mesh status speaks only when something is off ------------------------
def test_clean_mesh_shows_no_status():
    """A valid, unrepaired mesh is the normal case (watertight by construction
    since RNG-17), so an always-green badge says nothing. The status appears
    only for 'not castable' or 'auto-repaired'."""
    js = _js("app.js")
    fn = re.search(r"function renderMeshStatus\([^)]*\)\s*\{.*?\n\}", js, re.S).group(0)
    assert re.search(r"if \(valid && !repaired\)\s*\{\s*clearMeshStatus\(\);\s*return;", fn), (
        "renderMeshStatus must stay silent for a clean mesh"
    )
