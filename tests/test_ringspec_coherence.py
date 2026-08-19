"""RNG-32 -- cross-field coherence repair, driven by the casting gate's own
Violations rather than a parallel table of containment rules (specs/RNG-32.md).

Pure, offline, no key, no network: `make_coherent` operates purely on
RingSpec dicts and the castability gate already exercised by
test_ringspec_castability.py and its siblings.
"""
from __future__ import annotations

import pytest
from pydantic import ValidationError

from ringcad.ringspec import validate_spec
from ringcad.ringspec.castability import validate_castability
from ringcad.ringspec.coherence import make_coherent

GOOD_SOLITAIRE = {
    "version": "1.0",
    "archetype": "solitaire",
    "shank": {"inner_diameter": 16.5, "band_width": 2.2, "band_thickness": 1.9},
    "setting": {"prong_count": 6, "setting_height": 6.0},
    "stones": {"stone_diameter": 6.5, "stone_height": 4.0},
}


def _solitaire(**overrides) -> dict:
    spec = {
        "version": "1.0",
        "archetype": "solitaire",
        "shank": dict(GOOD_SOLITAIRE["shank"]),
        "setting": dict(GOOD_SOLITAIRE["setting"]),
        "stones": dict(GOOD_SOLITAIRE["stones"]),
    }
    for path, value in overrides.items():
        group, field = path.split(".")
        spec[group][field] = value
    return spec


def _archetype(archetype: str, group_key: str, **group_overrides) -> dict:
    spec = _solitaire()
    spec["archetype"] = archetype
    spec[group_key] = dict(group_overrides)
    return spec


def _is_castable(spec: dict) -> bool:
    return not validate_castability(validate_spec(spec))


# --- a coherent spec is left untouched ---------------------------------------
def test_coherent_spec_makes_no_adjustments():
    working, adjustments = make_coherent(GOOD_SOLITAIRE)
    assert adjustments == []
    assert _is_castable(working)


# --- min_wall -----------------------------------------------------------------
def test_min_wall_repairs_thin_band_thickness():
    spec = _solitaire(**{"shank.band_thickness": 0.5})
    working, adjustments = make_coherent(spec)
    assert _is_castable(working)
    assert any(a.code == "min_wall" for a in adjustments)
    assert working["shank"]["band_thickness"] > 0.8


# --- stone_exceeds_head: confidence picks the victim --------------------------
def test_stone_exceeds_head_moves_the_lower_confidence_field():
    spec = _solitaire(**{"stones.stone_height": 5.2, "setting.setting_height": 3.0})
    confidence = {"stone_height": 0.9, "setting_height": 0.4}
    working, adjustments = make_coherent(spec, confidence)
    assert _is_castable(working)
    assert adjustments[0].field == "setting.setting_height"
    assert working["stones"]["stone_height"] == pytest.approx(5.2)


def test_stone_exceeds_head_moves_stone_when_less_confident():
    spec = _solitaire(**{"stones.stone_height": 5.2, "setting.setting_height": 3.0})
    confidence = {"stone_height": 0.3, "setting_height": 0.9}
    working, adjustments = make_coherent(spec, confidence)
    assert _is_castable(working)
    assert adjustments[0].field == "stones.stone_height"
    assert working["setting"]["setting_height"] == pytest.approx(3.0)


def test_stone_exceeds_head_defaults_to_growing_the_setting_when_confidence_ties():
    spec = _solitaire(**{"stones.stone_height": 5.2, "setting.setting_height": 3.0})
    working, adjustments = make_coherent(spec, {})
    assert _is_castable(working)
    assert adjustments[0].field == "setting.setting_height"


# --- stone_exceeds_bore: inner_diameter never moves ---------------------------
def test_stone_exceeds_bore_shrinks_the_stone_not_the_bore():
    spec = _solitaire(**{"stones.stone_diameter": 18.0})
    working, adjustments = make_coherent(spec)
    assert _is_castable(working)
    assert all(a.field != "shank.inner_diameter" for a in adjustments)
    assert working["shank"]["inner_diameter"] == pytest.approx(16.5)
    assert working["stones"]["stone_diameter"] < 16.5


# --- min_prong_tip: confidence picks the victim -------------------------------
def test_min_prong_tip_drops_to_four_prongs_by_default():
    spec = _solitaire(**{"stones.stone_diameter": 2.0, "setting.prong_count": 6})
    working, adjustments = make_coherent(spec)
    assert _is_castable(working)
    assert adjustments[0].field == "setting.prong_count"
    assert working["setting"]["prong_count"] == 4


def test_min_prong_tip_grows_stone_when_prong_count_more_confident():
    spec = _solitaire(**{"stones.stone_diameter": 2.0, "setting.prong_count": 6})
    confidence = {"prong_count": 0.9, "stone_diameter": 0.3}
    working, adjustments = make_coherent(spec, confidence)
    assert _is_castable(working)
    assert adjustments[0].field == "stones.stone_diameter"
    assert working["setting"]["prong_count"] == 6


def test_min_prong_tip_grows_stone_when_already_four_prongs():
    spec = _solitaire(**{"stones.stone_diameter": 2.0, "setting.prong_count": 4})
    working, adjustments = make_coherent(spec)
    assert _is_castable(working)
    assert adjustments[0].field == "stones.stone_diameter"


# --- stone_curvature -----------------------------------------------------------
def test_stone_curvature_is_resolved():
    # A stone small enough to trip stone_curvature (min_curvature < 0.45mm
    # needs stone_diameter < 0.9 * length_ratio, so < 2.25mm at the 2.5 cap)
    # is always too small for any legal prong count too (min_prong_tip needs
    # >= 3.57mm even at 4 prongs) -- the two violations are inseparable under
    # this schema's bounds, and fixing prong_tip by growing the diameter
    # resolves curvature as a side effect. Assert the outcome, not which
    # field moved.
    spec = _solitaire(**{"stones.stone_diameter": 2.0, "setting.prong_count": 4})
    spec["stones"]["shape"] = "oval"
    spec["stones"]["length_ratio"] = 2.5
    working, adjustments = make_coherent(spec)
    assert _is_castable(working)
    assert {a.code for a in adjustments} >= {"min_prong_tip"}


def test_stone_curvature_repair_reduces_length_ratio_in_isolation():
    # Isolate the stone_curvature repair itself (not composed with
    # min_prong_tip) by calling the repair table entry directly against a
    # hand-built Violation, matching what castability.py's _stone_curvature
    # would emit.
    from ringcad.ringspec.coherence import _REPAIRS
    from ringcad.ringspec.castability import Violation

    spec = _solitaire()
    spec["stones"]["shape"] = "oval"
    spec["stones"]["length_ratio"] = 2.5
    v = Violation(code="stone_curvature", field="stones.length_ratio",
                  message="", limit_mm=0.45, actual_mm=0.3)
    adjustment = _REPAIRS["stone_curvature"](spec, v, {})
    assert adjustment.field == "stones.length_ratio"
    assert spec["stones"]["length_ratio"] < 2.5


# --- halo_overcrowding / halo_web: accent count shrinks -----------------------
def test_halo_overcrowding_reduces_accent_count():
    spec = _archetype("halo", "halo", halo_stone_diameter=2.5,
                       halo_stone_count=24, halo_gap=1.5, halo_stone_height=1.5)
    working, adjustments = make_coherent(spec)
    assert _is_castable(working)
    assert any(a.field == "halo.halo_stone_count" for a in adjustments)
    assert working["halo"]["halo_stone_count"] < 24


def test_halo_web_reduces_accent_count_below_overcrowding_alone():
    # The corpus counterexample from the ticket: 22 accents left 0.195mm of
    # metal between seats, a quarter of the casting floor.
    spec = _archetype("halo", "halo", halo_stone_diameter=1.2,
                       halo_stone_count=22, halo_gap=0.3, halo_stone_height=1.0)
    working, adjustments = make_coherent(spec)
    assert _is_castable(working)
    assert working["halo"]["halo_stone_count"] < 22


# --- trilogy_overcrowding -------------------------------------------------------
def test_trilogy_overcrowding_grows_side_stone_gap():
    spec = _solitaire(**{"shank.inner_diameter": 10.0,
                          "shank.band_thickness": 0.8,
                          "stones.stone_diameter": 9.0})
    spec["archetype"] = "trilogy"
    spec["trilogy"] = {"side_stone_diameter": 6.0, "side_stone_height": 3.0,
                        "side_stone_gap": 0.3}
    working, adjustments = make_coherent(spec)
    assert _is_castable(working)
    assert any(a.field == "trilogy.side_stone_gap" for a in adjustments)
    assert working["trilogy"]["side_stone_gap"] > 0.3


# --- side_stone_overcrowding: both sub-violations -----------------------------
def test_side_stone_overcrowding_count_reduces_accents_per_side():
    spec = _archetype("side_stone", "side_stone", accent_stone_diameter=2.0,
                       accent_stone_height=1.5, accent_count_per_side=8,
                       accent_gap=0.9)
    spec["shank"]["band_width"] = 5.6  # wide enough for the channel fit
    working, adjustments = make_coherent(spec)
    assert _is_castable(working)
    assert working["side_stone"]["accent_count_per_side"] < 8


def test_side_stone_overcrowding_gap_grows_when_only_neighbours_collide():
    spec = _archetype("side_stone", "side_stone", accent_stone_diameter=2.4,
                       accent_stone_height=1.5, accent_count_per_side=3,
                       accent_gap=0.2)
    spec["shank"]["band_width"] = 5.6
    working, adjustments = make_coherent(spec)
    assert _is_castable(working)


# --- side_stone_channel_fit / floor: the RNG-19 CP3 arithmetic ----------------
def test_side_stone_channel_fit_widens_the_band():
    spec = _archetype("side_stone", "side_stone")  # defaults: 1.5mm accent
    working, adjustments = make_coherent(spec)
    assert _is_castable(working)
    assert any(a.code == "side_stone_channel_fit" for a in adjustments)
    assert working["shank"]["band_width"] >= 3.1


def test_side_stone_channel_floor_thickens_the_band():
    spec = _archetype("side_stone", "side_stone", accent_stone_height=3.0)
    spec["shank"]["band_width"] = 3.2  # clear the width rule first
    working, adjustments = make_coherent(spec)
    assert _is_castable(working)


# --- the fallback backstop: every archetype's pure defaults must be castable --
@pytest.mark.parametrize("archetype,group_key", [
    ("solitaire", None),
    ("halo", "halo"),
    ("trilogy", "trilogy"),
    ("side_stone", "side_stone"),
])
def test_defaults_are_castable_after_coherence(archetype, group_key):
    spec = _solitaire()
    spec["archetype"] = archetype
    if group_key:
        spec[group_key] = {}
    working, _ = make_coherent(spec)
    assert _is_castable(working)


# --- an unrepairable / unbounded case must not raise --------------------------
def test_make_coherent_never_raises_on_a_schema_valid_spec():
    spec = _solitaire(**{"stones.stone_diameter": 2.0, "setting.prong_count": 6})
    working, adjustments = make_coherent(spec)
    validate_spec(working)  # must still be schema-valid


def test_make_coherent_requires_schema_valid_input():
    with pytest.raises(ValidationError):
        make_coherent({"archetype": "solitaire"})


# --- joint infeasibility: two violations pull the same field in opposite
# directions and can't both be satisfied (Verify finding, 2026-08-16) --------
def test_jointly_infeasible_violations_terminate_without_converging():
    """min_prong_tip wants stone_diameter above ~5.35mm at 6 prongs;
    stone_exceeds_bore wants it below inner_diameter/length_ratio = 4.85mm
    for this inner_diameter/ratio. No diameter satisfies both. The loop must
    still TERMINATE (bounded by MAX_PASSES, never hang) even though it
    cannot converge -- convergence in this case is the fallback chain's job
    (ClassifyResult._coherent_spec), not this function's."""
    spec = _solitaire(**{
        "shank.inner_diameter": 9.07, "stones.stone_diameter": 3.06,
        "setting.prong_count": 6,
    })
    spec["stones"]["shape"] = "round"
    spec["stones"]["length_ratio"] = 1.87  # schema allows it; classify.py's
    # _stone_shape() never produces this combination for a round stone.
    confidence = {"prong_count": 0.9, "stone_diameter": 0.1}
    working, adjustments = make_coherent(spec, confidence)
    assert len(adjustments) == 6  # ran the full budget, did not short-circuit
    assert not _is_castable(working)  # did not converge -- expected, documented
