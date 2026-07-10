"""RNG-10 Checkpoint 2 -- trilogy composition watertight-by-construction.

Mirrors `tests/test_halo_watertight.py` + `tests/test_halo_registration.py`'s
CP3 pattern for CP2: the `trilogy` module places two symmetric side settings
(`accent_seat` + 4 `accent_prong` each) on a gallery-post pedestal and fuses
them onto the centre setting for a SINGLE watertight castable trilogy -- no
floating side stones. The golden trilogy and a curated in-range band must each
be a single watertight manifold on RAW geometry (RNG-17 bar: NO
`validate_and_repair`).
"""
from __future__ import annotations

import pytest

from ringcad.geometry import compose
from ringcad.geometry._castability import check_accent_prong, check_accent_seat
from ringcad.geometry._common import clamps
from ringcad.geometry.module import ARCHETYPES, MODULES
from ringcad.geometry.trilogy import _side_locs, trilogy
from ringcad.ringspec import Setting, Shank, Stones, Trilogy, TrilogySpec, from_params

CANONICAL_PARAMS = {
    "inner_diameter": 16.5,
    "band_width": 2.2,
    "band_thickness": 1.9,
    "stone_diameter": 6.5,
    "stone_height": 4.0,
    "prong_count": 6,
    "setting_height": 6.0,
}

# Pre-CP2 solitaire baseline (RNG-16 compose target); parity must hold.
EXPECTED_VOLUME_MM3 = 389.56
VOLUME_TOL = 0.05  # +/-5%, the RNG-13 parity band

# Curated CASTABLE band: min/mid/max of each trilogy dimension in
# representative combos crossed with two center configs. Deliberately
# excludes the overcrowded corner the CP1 castability suite already flags
# (large side diameter + small gap on a small shank).
# (s_dia, s_height, s_gap, stone_dia, setting_h)
BAND = [
    (0.9, 0.8, 0.3, 6.5, 6.0),    # small side stones, tight gap, low setting
    (2.5, 1.8, 0.6, 6.5, 6.0),    # golden
    (6.0, 4.0, 2.0, 10.0, 6.0),   # big side stones, wide gap, wide center
    (0.9, 4.0, 2.0, 6.5, 3.0),    # small dia, deep well, sparse
    (6.0, 0.8, 0.3, 10.0, 3.0),   # big dia, shallow well, tight gap
    (2.5, 1.8, 2.0, 10.0, 6.0),
    (1.5, 2.5, 1.0, 6.5, 4.0),
]


def _trilogy_spec(*, s_dia=2.5, s_height=1.8, s_gap=0.6, stone_dia=6.5, setting_h=6.0):
    """The golden trilogy (solitaire defaults + trilogy defaults), overridable."""
    return TrilogySpec(
        shank=Shank(inner_diameter=16.5, band_width=2.2, band_thickness=1.9),
        setting=Setting(prong_count=6, setting_height=setting_h),
        stones=Stones(stone_diameter=stone_dia, stone_height=4.0),
        trilogy=Trilogy(
            side_stone_diameter=s_dia, side_stone_height=s_height,
            side_stone_gap=s_gap,
        ),
    )


def _assert_castable(result, label: str) -> None:
    assert result.body_count == 1, (
        f"{label}: body_count={result.body_count} (want 1)"
    )
    assert result.non_manifold_edges == 0, (
        f"{label}: non_manifold_edges={result.non_manifold_edges} (want 0)"
    )
    assert result.is_watertight, f"{label}: raw mesh is not watertight"


# ------------------------------------------------------------- registration
def test_trilogy_registered():
    """The trilogy composition registers with the fixed archetype order, and
    its check returns a list."""
    assert "trilogy" in MODULES
    assert ARCHETYPES["trilogy"] == ["shank", "seat", "prong_setting", "trilogy"]
    spec = _trilogy_spec()
    c = clamps(spec)
    result = MODULES["trilogy"].check(trilogy(spec, c), spec, c)
    assert isinstance(result, list)


def test_solitaire_parity_unchanged(raw_validate):
    """Adding trilogy leaves the solitaire archetype + its composed geometry
    unchanged -- same module order, same volume within parity, still a single
    watertight body."""
    assert ARCHETYPES["solitaire"] == ["shank", "seat", "prong_setting"]
    s = compose(from_params(CANONICAL_PARAMS))
    rel = abs(s.volume - EXPECTED_VOLUME_MM3) / EXPECTED_VOLUME_MM3
    assert rel < VOLUME_TOL, f"solitaire volume drifted: {s.volume:.2f}mm^3"
    assert len(s.solids()) == 1, "solitaire is no longer a single body"
    _assert_castable(raw_validate(s), "solitaire parity")


# ------------------------------------------------------------- watertight
def test_trilogy_module_two_side_bodies():
    """The trilogy module alone is two internally-fused side assemblies (left
    + right) that do NOT touch each other -- unlike halo's continuous rail
    ring, only the shank (added by `compose`) unites them into one body. Each
    side (post + seat + prongs) is its own single positive-volume body -- the
    fast loop before full compose."""
    spec = _trilogy_spec()
    solid = trilogy(spec, clamps(spec))
    assert len(solid.solids()) == 2, (
        "trilogy module should be exactly two disjoint side assemblies"
    )
    assert solid.volume > 0, "trilogy module has non-positive volume"


def test_golden_trilogy_single_watertight(raw_validate):
    """The raw golden `compose(trilogy_spec)` is a single watertight manifold
    -- asserted WITHOUT validate_and_repair; the posts make it one body, so no
    floating side stones. `.solids() == 1` + volume first, then the raw
    watertight bar."""
    spec = _trilogy_spec()
    s = compose(spec)
    assert len(s.solids()) == 1, "composed golden trilogy is not a single B-rep body"
    assert s.volume > 0, "composed golden trilogy has non-positive volume"
    _assert_castable(raw_validate(s), "golden trilogy compose")


@pytest.mark.parametrize("s_dia,s_height,s_gap,stone_dia,setting_h", BAND)
def test_trilogy_band_raw_watertight(
    raw_validate, s_dia, s_height, s_gap, stone_dia, setting_h
):
    """Across the curated in-range trilogy band each `compose(trilogy_spec)`
    is a single watertight body on raw geometry."""
    spec = _trilogy_spec(
        s_dia=s_dia, s_height=s_height, s_gap=s_gap,
        stone_dia=stone_dia, setting_h=setting_h,
    )
    s = compose(spec)
    label = (f"trilogy(dia={s_dia}, h={s_height}, gap={s_gap}, "
             f"sd={stone_dia}, gh={setting_h})")
    assert len(s.solids()) == 1, f"{label}: expected one B-rep body"
    assert s.volume > 0, f"{label}: non-positive B-rep volume"
    _assert_castable(raw_validate(s), label)


# ------------------------------------------------------------- side floors
@pytest.mark.parametrize("s_dia,s_height,s_gap,stone_dia,setting_h", BAND)
def test_trilogy_side_floors_hold(s_dia, s_height, s_gap, stone_dia, setting_h):
    """Across the in-range band, both side settings clear the min-wall /
    min-prong-tip floors by construction, via the reused accent checks
    (`check_trilogy`, the trilogy module's `_check`)."""
    spec = _trilogy_spec(
        s_dia=s_dia, s_height=s_height, s_gap=s_gap,
        stone_dia=stone_dia, setting_h=setting_h,
    )
    c = clamps(spec)
    solid = trilogy(spec, c)
    violations = MODULES["trilogy"].check(solid, spec, c)
    assert violations == [], (
        f"trilogy(dia={s_dia}, h={s_height}, gap={s_gap}) flagged: {violations}"
    )


def test_check_trilogy_ignores_non_trilogy_spec():
    """`check_trilogy` returns [] for a spec with no `trilogy` group (e.g. a
    plain SolitaireSpec routed through the same module.check call shape)."""
    from ringcad.geometry._castability import check_trilogy
    spec = from_params(CANONICAL_PARAMS)
    assert check_trilogy(object(), spec, clamps(spec)) == []


def test_side_locs_are_symmetric():
    """The two sides' seat locations are mirror images (opposite angular
    offset) around the same head radius -- a sanity check on Decision 4's
    `side_loc(sign)` before it drives geometry."""
    spec = _trilogy_spec()
    c = clamps(spec)
    left_seat, left_prongs = _side_locs(spec, c, -1.0)
    right_seat, right_prongs = _side_locs(spec, c, 1.0)
    assert len(left_prongs) == 4
    assert len(right_prongs) == 4
    left_pos = left_seat.position
    right_pos = right_seat.position
    # both sides sit at the same distance from the ring (finger) axis
    assert abs(
        (left_pos.X**2 + left_pos.Y**2) - (right_pos.X**2 + right_pos.Y**2)
    ) < 1e-6
    # and are not at the same position (genuinely offset apart)
    assert abs(left_pos.X - right_pos.X) > 1e-6 or abs(left_pos.Y - right_pos.Y) > 1e-6
