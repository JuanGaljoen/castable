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
def test_group_dims_clamped_to_model_bounds(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-test")
    # halo_stone_count 99 -> 24 (le), halo_stone_diameter 0.1 -> 0.9 (ge)
    _install_client(monkeypatch,
                    parsed_output=_halo(halo_stone_count=99,
                                        halo_stone_diameter=0.1))
    spec = classify_ring(IMG, JPEG).to_spec()
    assert spec["halo"]["halo_stone_count"] == 24
    assert spec["halo"]["halo_stone_diameter"] == 0.9


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
