"""The stone-shape control on the form (RNG-23 CP4).

Static structure + the JS source contract, matching the scope note in
tests/test_frontend.py: the Flask test client runs no JavaScript, so behaviour is
asserted by reading the script source for the contract it must implement, and the
live interaction is browser-QA'd.

Without this control the shape is unreachable by hand: a photo could set it but a
user could never correct it, which breaks the "estimates only, every field stays
editable" promise the photo flow makes.
"""
from __future__ import annotations

import os
import re

import pytest

from ringcad.app import create_app

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


@pytest.fixture
def html():
    client = create_app().test_client()
    return client.get("/").get_data(as_text=True)


def _source(name: str) -> str:
    with open(os.path.join(REPO_ROOT, "static", name)) as fh:
        return fh.read()


# --- the control exists and is reachable -----------------------------------

def test_shape_select_is_present():
    html = create_app().test_client().get("/").get_data(as_text=True)
    assert re.search(r'<select[^>]*id="shape"', html)


def test_shape_offers_every_cut_the_schema_can_express(html):
    """The select is read off the same Literal the spec validates against, so
    a cut the geometry can build cannot sit unreachable behind the form.

    Was `== ["round", "oval"]` until RNG-33 CP4, with the reasoning that other
    cuts "need a different prong primitive and must not be offered before they
    can be built". CP3 built that primitive -- the V-prong -- so the fence came
    down. Deriving the expected set rather than restating it means cut #7 fails
    here the moment the schema learns it, which is the whole point.
    """
    from ringcad.ringspec.cuts import profile_for  # noqa: F401
    from ringcad.classify import _BUILDABLE_SHAPES

    block = re.search(r'<select[^>]*id="shape".*?</select>', html, re.S)
    assert block, "no shape select found"
    values = re.findall(r'value="([^"]+)"', block.group(0))
    assert set(values) == set(_BUILDABLE_SHAPES), (
        f"form offers {sorted(values)}, schema expresses "
        f"{sorted(_BUILDABLE_SHAPES)}"
    )
    assert values[0] == "round", "round stays the default first option"


def test_length_ratio_input_is_present(html):
    assert re.search(r'<input[^>]*id="length_ratio"', html)


def test_length_ratio_is_bounded_to_the_schema_range(html):
    field = re.search(r'<input[^>]*id="length_ratio"[^>]*>', html, re.S)
    assert field, "no length_ratio input found"
    tag = field.group(0)
    assert 'min="1"' in tag or 'min="1.0"' in tag
    assert 'max="2.5"' in tag


# --- accessibility (WCAG 2.1 AA is mandatory in this repo) -----------------

@pytest.mark.parametrize("field_id", ["shape", "length_ratio"])
def test_each_control_has_a_label(html, field_id):
    assert re.search(rf'<label[^>]*for="{field_id}"', html)


@pytest.mark.parametrize("field_id", ["shape", "length_ratio"])
def test_each_control_has_a_described_by_hint(html, field_id):
    assert re.search(
        rf'id="{field_id}"[^>]*aria-describedby="{field_id}-hint"', html
    ) or re.search(
        rf'aria-describedby="{field_id}-hint"[^>]*id="{field_id}"', html
    )
    assert re.search(rf'id="{field_id}-hint"', html)


# --- the JS contract -------------------------------------------------------

def test_structured_body_sends_the_shape_fields():
    """Otherwise the control is decorative: the user picks oval and the request
    still asks for a round stone.

    The keys are contributed by `stoneShapeFields()` rather than written inline,
    because that helper also enforces "a round stone is always ratio 1.0". So the
    contract is asserted in two halves: the stones group pulls the helper in, and
    the helper emits both keys.
    """
    src = _source("app.js")
    stones = re.search(r"stones:\s*\{.*?\}", src, re.S)
    assert stones, "no stones group in the request body"
    assert "stoneShapeFields()" in stones.group(0)

    helper = re.search(r"function stoneShapeFields\(\).*?\n\}", src, re.S)
    assert helper, "no stoneShapeFields helper"
    assert "shape:" in helper.group(0)
    assert "length_ratio:" in helper.group(0)


def test_a_round_stone_never_sends_an_elongated_ratio():
    """A stale ratio left in the box must not elongate a round stone."""
    src = _source("app.js")
    helper = re.search(r"function stoneShapeFields\(\).*?\n\}", src, re.S)
    assert 'shape: "round", length_ratio: 1' in helper.group(0)


def test_shape_fields_are_read_from_the_form_not_hardcoded():
    src = _source("app.js")
    assert 'getElementById("shape")' in src
    assert 'getElementById("length_ratio")' in src


def test_every_selectable_style_sends_the_shape_fields():
    """The shape only reaches the server on the STRUCTURED request path.

    Solitaire was routed down the legacy flat-7 body, which has no stones group,
    so picking Oval on a solitaire silently produced a round ring -- on the
    default archetype, the one most users see. Caught by looking at a render, not
    by a test: the earlier tests asserted the fields existed in
    `gatherStructuredBody` without asking which styles actually use it.

    So assert the real invariant: every style offered in the form is handled by
    the structured path.
    """
    html = create_app().test_client().get("/").get_data(as_text=True)
    block = re.search(r'<select[^>]*id="archetype".*?</select>', html, re.S)
    assert block, "no archetype select found"
    offered = set(re.findall(r'value="([^"]+)"', block.group(0)))

    src = _source("app.js")
    registry = re.search(r"const ARCHETYPES = \{.*?\n\};", src, re.S)
    assert registry, "no ARCHETYPES registry"
    registered = set(re.findall(r"^  (\w+):", registry.group(0), re.M))

    missing = offered - registered
    assert not missing, (
        f"styles offered in the form but not in the structured registry: "
        f"{sorted(missing)} -- these send the legacy flat body and silently drop "
        "the stone shape"
    )


def test_photo_prefill_reenables_the_ratio_for_a_detected_oval():
    """`setField` assigns `.value` without dispatching an event, so prefilling
    the shape select alone leaves `length_ratio` DISABLED (its state is only
    recomputed on change). A detected oval would then show a ratio the user
    cannot correct, breaking the "estimates only, every field stays editable"
    promise. photo.js must fire the change, as it already does for archetype.
    """
    src = _source("photo.js")
    assert re.search(
        r'"shape"[\s\S]{0,200}dispatchEvent\(\s*new Event\("change"\)', src
    ), "photo.js must dispatch a change event after setting the shape select"


# --- the form's step grid must match the constant that rounds to it ---------

def test_the_length_ratio_input_declares_the_ratio_step_the_backend_rounds_to(html):
    """RNG-38's bug was a value the browser's number input silently refused,
    which blocked Generate with no error anywhere. The backend rounds every
    float onto a step grid so that cannot happen -- but only if the two agree,
    and nothing tied them together until this test (docs/adr/0002: a check that
    restates a number instead of reading it drifts).

    RNG-33 CP4 made them disagree for the first time: `length_ratio` moved to a
    0.01 grid so cushion's 1.02 and marquise's 1.95 survive the round trip, and
    the input had to move with it.
    """
    from ringcad.classify import RATIO_STEP

    field = re.search(r'<input[^>]*id="length_ratio"[^>]*>', html, re.S)
    assert field, "no length_ratio input found"
    assert f'step="{RATIO_STEP}"' in field.group(0), (
        f'length_ratio must declare step="{RATIO_STEP}", the grid '
        f"classify._round_to_step snaps it to; got {field.group(0)}"
    )


# --- the cut bands are served, not retyped (RNG-33 CP4) --------------------

def test_every_option_carries_its_cuts_band_as_data_attributes(html):
    """The form has to DEFAULT and BOUND the ratio per cut, and those numbers
    already live in `ringcad.ringspec.cuts`. Serving them onto the options is
    what stops a second copy appearing in JS and drifting the first time a band
    moves (docs/adr/0002)."""
    from ringcad.ringspec.cuts import cut_catalogue

    block = re.search(r'<select[^>]*id="shape".*?</select>', html, re.S)
    assert block, "no shape select found"
    for cut in cut_catalogue():
        option = re.search(
            r'<option value="%s".*?</option>' % re.escape(cut["name"]),
            block.group(0), re.S)
        assert option, f"no option for {cut['name']}"
        tag = option.group(0)
        assert f'data-default-ratio="{cut["default_ratio"]}"' in tag
        assert f'data-min-ratio="{cut["min_ratio"]}"' in tag
        assert f'data-max-ratio="{cut["max_ratio"]}"' in tag


def test_the_ratio_bounds_are_read_from_the_option_not_written_in_js():
    src = _source("app.js")
    helper = re.search(r"function applyShapeState\(\).*?\n\}", src, re.S)
    assert helper, "no applyShapeState helper"
    body = helper.group(0)
    assert "dataset.minRatio" in body and "dataset.maxRatio" in body
    assert "dataset.defaultRatio" in body
    # No cut name may appear in the helper: that would be a band by another name.
    for name in ("cushion", "emerald", "pear", "marquise"):
        assert name not in body, (
            f"applyShapeState mentions {name}; per-cut facts belong on the "
            "option, not in the handler"
        )


def test_changing_cut_does_not_discard_a_ratio_the_photo_flow_measured():
    """`photo.js` pre-fills every field and THEN dispatches `change` on the
    shape select so the ratio's enabled state is recomputed. If that handler
    reset the ratio unconditionally, every upload would silently replace
    vision's measured elongation with a textbook default -- and the form would
    look like it had worked, which is the RNG-23 class of bug exactly.

    So the reset must be conditional on the value being outside the new cut's
    band.
    """
    src = _source("app.js")
    helper = re.search(r"function applyShapeState\(\).*?\n\}", src, re.S)
    body = helper.group(0)
    assert re.search(r"if\s*\(!\(current >= lo && current <= hi\)\)", body), (
        "applyShapeState must only fall back to the cut default when the "
        "current ratio is outside the cut's band"
    )


def test_a_cushion_at_ratio_one_is_still_sent_as_a_cushion():
    """The oval-at-1.0 collapse is about OVAL. A square cushion is genuinely
    1.00 and is not a circle, so the helper must special-case oval by name
    rather than collapsing every cut at 1.0."""
    src = _source("app.js")
    helper = re.search(r"function stoneShapeFields\(\).*?\n\}", src, re.S)
    body = helper.group(0)
    assert 'shape === "oval"' in body, (
        "the ratio-1.0 collapse must name oval; collapsing any cut at 1.0 "
        "would turn a square cushion into a round stone"
    )
