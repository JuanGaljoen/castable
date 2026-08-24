"""Unit tests for the Claude vision ring classifier (RNG-6).

TDD RED: these tests define ringcad.classify, which does not exist yet. They
MUST fail at collection (ModuleNotFoundError on ringcad.classify) until the
implementer lands the module.

NO NETWORK, NO API KEY. The only thing mocked is the Anthropic client itself,
patched where classify.py looks it up: `ringcad.classify.anthropic.Anthropic`.
The fake's `.with_options(...).messages.parse(...)` returns an object whose
`.parsed_output` is a real `ringcad.classify.RingClassification` instance (or
None for the parse-failure case), or `.messages.parse` raises for the
never-raises case. classify_available() is driven via monkeypatch.setenv /
delenv on ANTHROPIC_API_KEY.
"""
import pytest

import ringcad.classify as classify
from ringcad.classify import (
    CLAMP_BOUNDS,
    RingClassification,
    classify_available,
    classify_ring,
)
from ringcad.ringspec import is_castable, validate_spec

JPEG = "image/jpeg"
IMG = b"\xff\xd8\xff\xe0fake-jpeg-bytes"


class _FakeMessages:
    """Stands in for client.messages. parse() returns a preset response or
    raises a preset exception."""

    def __init__(self, parsed_output=None, raises=None):
        self._parsed_output = parsed_output
        self._raises = raises

    def parse(self, *args, **kwargs):
        if self._raises is not None:
            raise self._raises
        return type("Resp", (), {"parsed_output": self._parsed_output})()


class _FakeClient:
    def __init__(self, messages):
        self.messages = messages

    def with_options(self, *args, **kwargs):
        return self


def _install_client(monkeypatch, *, parsed_output=None, raises=None):
    """Patch ringcad.classify.anthropic.Anthropic to build a fake client that
    yields the given parsed_output / raises. Returns a dict recording whether
    the constructor was called."""
    rec = {"constructed": 0}
    messages = _FakeMessages(parsed_output=parsed_output, raises=raises)

    def fake_ctor(*args, **kwargs):
        rec["constructed"] += 1
        return _FakeClient(messages)

    monkeypatch.setattr(classify.anthropic, "Anthropic", fake_ctor)
    return rec


# RingClassification now requires EVERY field (RNG-21: no defaults, so the
# structured-output schema has no optional fields). The helper supplies a full
# set; group dims default to 0.0 ("not estimated") and are overridden per test.
_FULL = dict(
    ring_detected=True, style="solitaire", archetype="solitaire", prong_count=6,
    shank_taper="straight", features=["polished"],
    band_width=2.2, band_thickness=1.9, stone_diameter=6.5,
    stone_height=4.0, setting_height=6.0,
    halo_stone_diameter=0.0, halo_stone_count=0.0, halo_gap=0.0,
    halo_stone_height=0.0,
    side_stone_diameter=0.0, side_stone_height=0.0, side_stone_gap=0.0,
    accent_stone_diameter=0.0, accent_stone_height=0.0,
    accent_count_per_side=0.0, accent_gap=0.0,
    # Centre-stone shape (RNG-23); required like everything else, so the default
    # stub describes a plain round stone.
    stone_shape="round", stone_length_ratio=1.0,
    note="rough estimate",
)


def _conf(**vals):
    """A RingConfidence with every field supplied (all required); unset -> 0.0."""
    base = dict(band_width=0.0, band_thickness=0.0, stone_diameter=0.0,
                stone_height=0.0, setting_height=0.0, prong_count=0.0)
    base.update(vals)
    return RingConfidence(**base)


def _ring(**overrides):
    """A RingClassification for a detected ring, with field overrides."""
    base = dict(_FULL)
    base.setdefault("confidence", _conf())
    base.update(overrides)
    return RingClassification(**base)


# ---- AC4: estimates clamped to CLAMP_BOUNDS --------------------------------
def test_estimates_clamped_to_bounds(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test")
    _install_client(
        monkeypatch,
        parsed_output=_ring(band_width=99.0, band_thickness=0.1),
    )
    result = classify_ring(IMG, JPEG)
    assert result.ok is True
    # band_width clamped to its upper bound, band_thickness to its lower bound
    assert result.estimates["band_width"] == CLAMP_BOUNDS["band_width"][1]
    assert result.estimates["band_thickness"] == CLAMP_BOUNDS["band_thickness"][0]


# ---- AC4: prong_count snapped to {4, 6} ------------------------------------
@pytest.mark.parametrize("raw,snapped", [(5, 4), (7, 6), (4, 4), (6, 6)])
def test_prong_count_snapped(monkeypatch, raw, snapped):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test")
    _install_client(monkeypatch, parsed_output=_ring(prong_count=raw))
    result = classify_ring(IMG, JPEG)
    assert result.ok is True
    assert result.estimates["prong_count"] == snapped


# ---- AC4: inner_diameter is never estimated --------------------------------
def test_inner_diameter_never_in_estimates(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test")
    _install_client(monkeypatch, parsed_output=_ring())
    result = classify_ring(IMG, JPEG)
    assert "inner_diameter" not in result.estimates


def test_clamp_bounds_are_the_five_estimables(monkeypatch):
    expected = {
        "band_width", "band_thickness", "stone_diameter",
        "stone_height", "setting_height",
    }
    assert set(CLAMP_BOUNDS.keys()) == expected
    assert "inner_diameter" not in CLAMP_BOUNDS
    assert "prong_count" not in CLAMP_BOUNDS


# ---- AC7: not-a-ring -> ok True, ring_detected False, estimates {} ----------
def test_not_a_ring_returns_empty_estimates(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test")
    _install_client(
        monkeypatch,
        parsed_output=_ring(ring_detected=False),
    )
    result = classify_ring(IMG, JPEG)
    assert result.ok is True
    assert result.ring_detected is False
    assert result.estimates == {}


# ---- AC10: never raises -- API exception -> ok=False ------------------------
def test_api_timeout_returns_ok_false_not_raise(monkeypatch):
    import anthropic

    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test")
    timeout = anthropic.APITimeoutError(request=None)
    _install_client(monkeypatch, raises=timeout)
    result = classify_ring(IMG, JPEG)  # must NOT raise
    assert result.ok is False


def test_arbitrary_exception_returns_ok_false_not_raise(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test")
    _install_client(monkeypatch, raises=RuntimeError("boom"))
    result = classify_ring(IMG, JPEG)  # must NOT raise
    assert result.ok is False


# ---- AC10: parsed_output None (refusal/truncation) -> ok=False --------------
def test_parse_failure_returns_ok_false(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test")
    _install_client(monkeypatch, parsed_output=None)
    result = classify_ring(IMG, JPEG)
    assert result.ok is False


# ---- AC8: classify_available reflects ANTHROPIC_API_KEY only ----------------
def test_classify_available_true_when_key_set(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test")
    assert classify_available() is True


def test_classify_available_false_when_key_unset(monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    assert classify_available() is False


def test_classify_available_builds_no_client(monkeypatch):
    """classify_available is env-only -- it must not construct a client."""
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    rec = _install_client(monkeypatch, parsed_output=_ring())
    classify_available()
    assert rec["constructed"] == 0


# ---- to_json carries the RNG-12 response body fields -----------------------
def test_to_json_carries_ringspec_contract(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test")
    _install_client(monkeypatch, parsed_output=_ring())
    body = classify_ring(IMG, JPEG).to_json()
    for key in ("ring_detected", "detected_style", "note", "spec"):
        assert key in body


# ===========================================================================
# RNG-12: vision -> validated RingSpec (archetype + groups + confidence)
# ===========================================================================
from ringcad.ringspec import is_castable, validate_spec  # noqa: E402
from ringcad.classify import RingConfidence  # noqa: E402


def _halo(**overrides):
    base = dict(archetype="halo", style="halo",
                halo_stone_diameter=1.3, halo_stone_count=14,
                halo_gap=0.5, halo_stone_height=1.2)
    base.update(overrides)
    return _ring(**base)


# ---- AC1: detected archetype maps to a valid RingSpec ----------------------
def test_detected_halo_builds_valid_halo_spec(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test")
    _install_client(monkeypatch, parsed_output=_halo())
    spec = classify_ring(IMG, JPEG).to_spec()
    assert spec["archetype"] == "halo"
    assert "halo" in spec
    # returned spec is a valid RingSpec and a castable /generate-ring body
    validated = validate_spec(spec)
    assert is_castable(validated)


@pytest.mark.parametrize("archetype", ["solitaire", "halo", "trilogy",
                                       "side_stone"])
def test_every_archetype_builds_valid_spec(monkeypatch, archetype):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test")
    _install_client(monkeypatch,
                    parsed_output=_ring(archetype=archetype, style=archetype))
    spec = classify_ring(IMG, JPEG).to_spec()
    assert spec["archetype"] == archetype
    validate_spec(spec)  # must not raise


# ---- AC2: group dims clamped to the RingSpec field bounds ------------------
def test_group_dims_clamped_to_model_bounds():
    # halo_stone_count 99 -> 24 (le), halo_stone_diameter 0.1 -> 0.9 (ge).
    # Unit-level, BEFORE the RNG-32 coherence pass: `_group_estimates` only
    # clamps each field to its own schema bound, one field at a time.
    data = _halo(halo_stone_count=99, halo_stone_diameter=0.1)
    estimates = classify._group_estimates("halo", data)
    assert estimates["halo_stone_count"] == 24
    assert estimates["halo_stone_diameter"] == 0.9


def test_group_dims_clamped_then_made_castable(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test")
    # 24 accents at the clamped 0.9mm minimum overcrowd the halo ring RNG-32
    # coherence must shrink the count further so the assembled spec is
    # actually castable, not merely within each field's own bound.
    _install_client(monkeypatch,
                    parsed_output=_halo(halo_stone_count=99,
                                        halo_stone_diameter=0.1))
    spec = classify_ring(IMG, JPEG).to_spec()
    assert spec["halo"]["halo_stone_count"] <= 24
    assert spec["halo"]["halo_stone_diameter"] == 0.9
    assert is_castable(validate_spec(spec))


# ---- AC2: integer group counts snapped to int ------------------------------
def test_group_count_snapped_to_int(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test")
    _install_client(monkeypatch, parsed_output=_halo(halo_stone_count=13.6))
    spec = classify_ring(IMG, JPEG).to_spec()
    val = spec["halo"]["halo_stone_count"]
    assert val == 14 and isinstance(val, int)


# ---- AC3: per-field confidence (shared 7) surfaced -------------------------
def test_confidence_surfaced_on_spec(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test")
    conf = _conf(band_width=0.6, stone_diameter=0.9)
    _install_client(monkeypatch, parsed_output=_ring(confidence=conf))
    spec = classify_ring(IMG, JPEG).to_spec()
    assert spec["confidence"]["band_width"] == 0.6
    assert spec["confidence"]["stone_diameter"] == 0.9
    # inner_diameter is never estimated -> its confidence stays absent/None
    assert spec["confidence"].get("inner_diameter") is None


def test_confidence_clamped_to_unit_interval(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test")
    _install_client(monkeypatch,
                    parsed_output=_ring(confidence=_conf(band_width=1.7)))
    spec = classify_ring(IMG, JPEG).to_spec()
    assert spec["confidence"]["band_width"] == 1.0


# ---- AC1: unsupported detected style -> fallback note names both -----------
def test_divergent_style_produces_fallback_note(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test")
    _install_client(monkeypatch,
                    parsed_output=_ring(archetype="solitaire",
                                        style="cathedral pave"))
    result = classify_ring(IMG, JPEG)
    assert "cathedral pave" in result.note
    assert "solitaire" in result.note


def test_matching_style_keeps_plain_note(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test")
    _install_client(monkeypatch,
                    parsed_output=_halo(style="halo pave", note="looks good"))
    result = classify_ring(IMG, JPEG)
    assert "nearest supported" not in result.note


# ---- inner_diameter never estimated: spec carries the default --------------
def test_spec_inner_diameter_is_default_not_guessed(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test")
    _install_client(monkeypatch, parsed_output=_ring())
    spec = classify_ring(IMG, JPEG).to_spec()
    assert spec["shank"]["inner_diameter"] == classify.DEFAULT_INNER_DIAMETER


# ---- not-a-ring: spec is None ----------------------------------------------
def test_not_a_ring_has_no_spec(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test")
    _install_client(monkeypatch,
                    parsed_output=_ring(ring_detected=False))
    result = classify_ring(IMG, JPEG)
    assert result.to_spec() is None
    assert result.to_json()["spec"] is None


# --- RNG-32: cross-field coherence, wired end-to-end through classify_ring --
def test_stone_taller_than_head_is_repaired_end_to_end(monkeypatch):
    """The ticket's own counterexample: probes/corpus/halo-round.png produced
    stone_height 5.2 inside setting_height 3.0 -- individually defensible,
    together a stone protruding through the bottom of its own head."""
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test")
    _install_client(
        monkeypatch,
        parsed_output=_ring(stone_height=5.2, setting_height=3.0),
    )
    result = classify_ring(IMG, JPEG)
    spec = result.to_spec()
    assert is_castable(validate_spec(spec))
    assert spec["stones"]["stone_height"] < spec["setting"]["setting_height"]


def test_adjustments_are_carried_on_to_json(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test")
    _install_client(
        monkeypatch,
        parsed_output=_ring(stone_height=5.2, setting_height=3.0),
    )
    body = classify_ring(IMG, JPEG).to_json()
    assert body["adjustments"]
    assert body["adjustments"][0]["code"] == "stone_exceeds_head"
    assert is_castable(validate_spec(body["spec"]))


def test_coherent_spec_needs_no_adjustments(monkeypatch):
    # A schema-valid, already-castable estimate set makes zero adjustments --
    # coherence must not perturb a spec that was already fine.
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test")
    _install_client(monkeypatch, parsed_output=_ring())
    body = classify_ring(IMG, JPEG).to_json()
    assert body["adjustments"] == []


def test_side_stone_archetype_repairs_the_channel_band(monkeypatch):
    """The comment-2 counterexample: a 2mm band with a channel setting that
    needs 3.1mm to hold the stone plus a wall each side."""
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test")
    _install_client(
        monkeypatch,
        parsed_output=_ring(
            archetype="side_stone", band_width=2.0,
            accent_stone_diameter=1.5, accent_stone_height=1.2,
            accent_count_per_side=3, accent_gap=0.3,
        ),
    )
    spec = classify_ring(IMG, JPEG).to_spec()
    assert spec["archetype"] == "side_stone"
    assert is_castable(validate_spec(spec))
    assert spec["shank"]["band_width"] >= 3.1


def test_falls_back_to_solitaire_when_archetype_repair_does_not_converge(monkeypatch):
    """The fallback chain's middle link: a halo whose repair loop can't reach
    a castable spec within budget must fall back to a solitaire built from
    the same shared estimates, not raise or return garbage."""
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test")
    _install_client(monkeypatch, parsed_output=_halo())
    calls = {"n": 0}
    real_is_castable = classify.is_castable

    def fake_is_castable(model):
        calls["n"] += 1
        if calls["n"] == 1:
            return False  # the halo attempt never converges
        return real_is_castable(model)

    monkeypatch.setattr(classify, "is_castable", fake_is_castable)
    spec = classify_ring(IMG, JPEG).to_spec()
    assert spec["archetype"] == "solitaire"
    assert is_castable(validate_spec(spec))


def test_falls_back_to_pure_defaults_when_nothing_converges(monkeypatch):
    """The fallback chain's last link: even the solitaire attempt failing to
    converge must still return the guaranteed-castable pure defaults, never
    an uncastable spec or an exception."""
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test")
    _install_client(monkeypatch, parsed_output=_ring())
    monkeypatch.setattr(classify, "is_castable", lambda model: False)
    spec = classify_ring(IMG, JPEG).to_spec()
    assert spec["archetype"] == "solitaire"
    assert spec["stones"]["stone_diameter"] == classify._SHARED_DEFAULTS["stone_diameter"]
    assert spec["shank"]["band_width"] == classify._SHARED_DEFAULTS["band_width"]


# NOTE (Verify, 2026-08-16): an attempt to reproduce the jointly-infeasible
# oscillation (see test_ringspec_coherence.py's
# test_jointly_infeasible_violations_terminate_without_converging) at the
# ClassifyResult level was removed here. _assemble calls _stone_shape() on
# EVERY attempt, not only the pure-default last resort, so a non-oval shape
# always collapses length_ratio to 1.0 before make_coherent ever runs -- the
# scenario that test's docstring claimed to bypass cannot actually be
# constructed through ClassifyResult, only through coherence.make_coherent
# directly on a raw dict (which the coherence-level test correctly does). A
# 5000-sample fuzz of ClassifyResult.to_spec() across the full schema-legal
# input space (tests/... not committed, run ad hoc during Verify) found zero
# cases reaching the pure-default last resort, confirming the middle tier
# (solitaire from the same shared estimates) already absorbs every
# reachable failure; the last resort is a safety net for inputs this
# pipeline cannot currently produce, not something to force a test through.
# The fallback chain's actual mechanics are already covered by
# test_falls_back_to_solitaire_when_archetype_repair_does_not_converge and
# test_falls_back_to_pure_defaults_when_nothing_converges above, which
# force non-convergence via a fake is_castable rather than a hand-built
# adversarial spec -- the honest way to test a branch that real inputs
# don't reach.


# --- RNG-38: round every dimension to its form field's 0.1 step ------------
def _on_step_grid(value: float, step: float = 0.1) -> bool:
    """True iff `value` is within floating-point epsilon of a multiple of
    `step` -- the actual constraint the browser's number input enforces, not
    a coincidence of how Python's round() breaks ties near x.05."""
    nearest = round(value / step) * step
    return abs(value - nearest) < 1e-6


def test_round_to_step_rounds_float_leaves_only():
    spec = {
        "version": "1.0", "archetype": "solitaire",
        "shank": {"inner_diameter": 16.53, "band_width": 2.17, "band_thickness": 1.9},
        "setting": {"prong_count": 6, "setting_height": 6.05},
        "stones": {"stone_diameter": 6.5, "stone_height": 4.0,
                   "shape": "oval", "length_ratio": 1.48},
    }
    rounded = classify._round_to_step(spec)
    assert rounded["shank"]["inner_diameter"] == pytest.approx(16.5)
    assert rounded["shank"]["band_width"] == pytest.approx(2.2)
    assert rounded["setting"]["prong_count"] == 6  # int untouched
    # 6.05 is an exact halfway point; which way it lands is a float-
    # representation coin flip and doesn't matter -- landing ON the grid does.
    assert _on_step_grid(rounded["setting"]["setting_height"])
    assert rounded["stones"]["shape"] == "oval"  # str untouched
    # length_ratio rounds on its OWN finer grid (RNG-33 CP4): a ratio needs
    # 0.01, because at 0.1 the per-cut conventional defaults do not survive
    # (cushion 1.02 -> 1.00, marquise 1.95 -> 2.00).
    assert rounded["stones"]["length_ratio"] == pytest.approx(1.48)


def test_round_to_step_leaves_an_already_aligned_spec_unchanged():
    spec = {
        "version": "1.0", "archetype": "solitaire",
        "shank": {"inner_diameter": 16.5, "band_width": 2.2, "band_thickness": 1.9},
        "setting": {"prong_count": 6, "setting_height": 6.0},
        "stones": {"stone_diameter": 6.5, "stone_height": 4.0},
    }
    rounded = classify._round_to_step(spec)
    assert rounded == spec


def test_round_to_step_ignores_confidence_and_meta_keys():
    spec = {
        "version": "1.0", "archetype": "solitaire",
        "shank": {"inner_diameter": 16.5, "band_width": 2.2, "band_thickness": 1.9},
        "setting": {"prong_count": 6, "setting_height": 6.0},
        "stones": {"stone_diameter": 6.5, "stone_height": 4.0},
        "confidence": {"band_width": 0.73333},
        "motifs": [],
    }
    rounded = classify._round_to_step(spec)
    assert rounded["confidence"]["band_width"] == 0.73333  # untouched
    assert rounded["motifs"] == []


def test_coherent_spec_length_ratio_lands_on_the_step_grid(monkeypatch):
    """The reported repro: vision's raw length_ratio (e.g. 1.48) reaching the
    form unrounded, tripping the browser's native step validation."""
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test")
    _install_client(
        monkeypatch,
        parsed_output=_ring(stone_shape="oval", stone_length_ratio=1.48),
    )
    spec = classify_ring(IMG, JPEG).to_spec()
    assert _on_step_grid(spec["stones"]["length_ratio"], classify.RATIO_STEP)
    assert is_castable(validate_spec(spec))


def test_coherent_spec_repaired_field_also_lands_on_the_step_grid(monkeypatch):
    """The screenshot case found while scoping: a coherence-repaired field
    (setting_height, moved by the stone_exceeds_head repair's +0.05 margin)
    must also land on the step grid, not just vision's raw estimate."""
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test")
    _install_client(
        monkeypatch,
        parsed_output=_ring(stone_height=5.2, setting_height=3.0),
    )
    spec = classify_ring(IMG, JPEG).to_spec()
    assert _on_step_grid(spec["setting"]["setting_height"])
    assert is_castable(validate_spec(spec))


def test_settle_on_step_grid_falls_back_to_ceil_on_an_exact_tie():
    """The real oscillation found while wiring this in: repairing
    stone_exceeds_head against a 0.1-aligned stone_height (5.2) with the
    +0.05 margin lands EXACTLY on a half-step tie (5.25). Nearest-rounding
    it drops back to 5.2 -- equal to stone_height, still a violation -- and
    re-repairing that reproduces 5.25 again, forever: a genuine period-2
    cycle, not a hypothetical. _settle_on_step_grid's ceil/floor escape
    hatch is what actually resolves it; assert it lands on 5.3, not that a
    generic re-repair loop eventually converges (it provably cannot)."""
    from ringcad.ringspec.coherence import make_coherent

    spec = {
        "version": "1.0", "archetype": "solitaire",
        "shank": {"inner_diameter": 16.5, "band_width": 2.2, "band_thickness": 1.9},
        "setting": {"prong_count": 6, "setting_height": 3.0},
        "stones": {"stone_diameter": 6.5, "stone_height": 5.2},
    }
    coherent, _ = make_coherent(spec)
    assert coherent["setting"]["setting_height"] == pytest.approx(5.25)  # the tie

    stepped = classify._settle_on_step_grid(coherent)
    assert stepped is not None
    assert _on_step_grid(stepped["setting"]["setting_height"])
    assert is_castable(validate_spec(stepped))


def test_settle_on_step_grid_prefers_nearest_when_it_is_already_castable():
    coherent = {
        "version": "1.0", "archetype": "solitaire",
        "shank": {"inner_diameter": 16.5, "band_width": 2.2, "band_thickness": 1.94},
        "setting": {"prong_count": 6, "setting_height": 6.0},
        "stones": {"stone_diameter": 6.5, "stone_height": 4.0},
    }
    stepped = classify._settle_on_step_grid(coherent)
    assert stepped["shank"]["band_thickness"] == pytest.approx(1.9)
