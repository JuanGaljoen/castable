"""RNG-11 Checkpoint 2 -- side-stone (channel) composition watertight-by-construction.

Mirrors `tests/test_trilogy.py`'s CP2 pattern: the `side_stone` module places
a symmetric accent row down each shoulder, retained by channel-wall rails
welded THROUGH the shank (no gallery, no accent_prong -- specs/RNG-11.md
Decisions 3/4), and fuses them onto the centre setting for a SINGLE watertight
castable side-stone band -- no floating accents. The golden band and a curated
in-range band must each be a single watertight manifold on RAW geometry
(RNG-17 bar: NO `validate_and_repair`).
"""
from __future__ import annotations

import pytest

from ringcad.geometry import compose
from ringcad.geometry._common import MIN_WALL, clamps
from ringcad.geometry.module import ARCHETYPES, MODULES
from ringcad.geometry.side_stone import _accent_angles, _trench_span
from ringcad.ringspec import Setting, Shank, SideStone, SideStoneSpec, Stones, from_params
from ringcad.ringspec.models import channel_groove_depth

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
# Was the spike-measured 389.56; REBASELINED in RNG-19 CP1 (2026-08-05)
# when the shank stopped tapering in thickness. See
# tests/test_geometry_parity.py for the before/after and the reasoning.
EXPECTED_VOLUME_MM3 = 279.62
VOLUME_TOL = 0.05  # +/-5%, the RNG-13 parity band

# Curated CASTABLE band: min/mid/max of each side_stone dimension in
# representative combos. Deliberately excludes the overcrowded corner the CP1
# castability suite already flags (large diameter + small gap on a small
# shank), and the widest-diameter/tightest-gap combos that would flag under
# `_side_stone_overcrowding` per CP1's chord/arc check.
# (a_dia, a_height, a_count, a_gap)
BAND = [
    (0.9, 0.8, 1, 0.2),    # smallest accents, single accent, tight gap
    (1.5, 1.2, 3, 0.3),    # golden
    (2.5, 3.0, 2, 1.0),    # large accents, deep well, wide gap
    (0.9, 3.0, 4, 1.0),    # small diameter, deep well, several accents
    (2.5, 0.8, 2, 1.0),    # large diameter, shallow well
    (1.5, 2.5, 5, 0.5),
]


def _side_stone_spec(*, a_dia=1.5, a_height=1.2, a_count=3, a_gap=0.3,
                      band_thickness=None, stone_dia=6.5, setting_h=6.0):
    """The golden side-stone band, on a band that can actually HOLD its channel.

    RNG-19 CP3 made the band size a hard constraint rather than a free choice:
    a channel is cut INTO the band, so it needs `a_dia + 2*MIN_WALL` of width
    and `groove_depth + MIN_WALL` of thickness. The old fixed 2.2mm band cannot
    hold any legal accent, which is exactly why RNG-11 shipped raised beads.
    Both dimensions are therefore derived, not hardcoded.
    """
    band_width = a_dia + 2 * MIN_WALL + 0.1
    fits = channel_groove_depth(a_height) + MIN_WALL + 0.1
    band_thickness = fits if band_thickness is None else max(band_thickness, fits)
    return SideStoneSpec(
        shank=Shank(inner_diameter=16.5, band_width=band_width,
                    band_thickness=band_thickness),
        setting=Setting(prong_count=6, setting_height=setting_h),
        stones=Stones(stone_diameter=stone_dia, stone_height=4.0),
        side_stone=SideStone(
            accent_stone_diameter=a_dia, accent_stone_height=a_height,
            accent_count_per_side=a_count, accent_gap=a_gap,
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
def test_side_stone_registered():
    """The side_stone composition registers with the fixed archetype order,
    and its check returns a list."""
    assert "side_stone" in MODULES
    assert ARCHETYPES["side_stone"] == [
        "shank", "seat", "prong_setting", "side_stone",
    ]
    spec = _side_stone_spec()
    c = clamps(spec)
    from ringcad.geometry.side_stone import side_stone
    result = MODULES["side_stone"].check(side_stone(spec, c), spec, c)
    assert isinstance(result, list)


def test_solitaire_parity_unchanged(raw_validate):
    """Adding side_stone leaves the solitaire archetype + its composed
    geometry unchanged -- same module order, same volume within parity, still
    a single watertight body."""
    assert ARCHETYPES["solitaire"] == ["shank", "seat", "prong_setting"]
    s = compose(from_params(CANONICAL_PARAMS))
    rel = abs(s.volume - EXPECTED_VOLUME_MM3) / EXPECTED_VOLUME_MM3
    assert rel < VOLUME_TOL, f"solitaire volume drifted: {s.volume:.2f}mm^3"
    assert len(s.solids()) == 1, "solitaire is no longer a single body"
    _assert_castable(raw_validate(s), "solitaire parity")


# ------------------------------------------------------------- watertight
def test_golden_side_stone_single_watertight(raw_validate):
    """The raw golden `compose(side_stone_spec)` is a single watertight
    manifold -- asserted WITHOUT validate_and_repair. Every accent seat and
    channel-wall rail welds through the shank, so no floating accents.
    `.solids() == 1` + volume first, then the raw watertight bar."""
    spec = _side_stone_spec()
    s = compose(spec)
    assert len(s.solids()) == 1, "composed golden side-stone band is not a single B-rep body"
    assert s.volume > 0, "composed golden side-stone band has non-positive volume"
    _assert_castable(raw_validate(s), "golden side-stone compose")


def test_side_stone_channel_is_cut_into_the_band():
    """DELIBERATELY INVERTED in RNG-19 CP3 (was `..._accents_are_proud_not_
    buried`). RNG-11 built raised beads, so it asserted the band gained volume
    over a bare solitaire. A channel is a groove, so it must LOSE volume.

    The guard's purpose is unchanged and still load-bearing: it catches a
    side-stone band that is silently identical to a plain solitaire. Only the
    sign of the expected difference moved, because the construction did."""
    spec = _side_stone_spec()
    band = compose(spec)
    bare = compose(spec, archetype="solitaire")
    removed = bare.volume - band.volume
    assert removed > 2.0, (
        f"the channel removes only {removed:.2f}mm^3 from the band -- it is "
        "not a groove, and this ring is effectively a plain solitaire"
    )


@pytest.mark.parametrize("a_dia,a_height,a_count,a_gap", BAND)
def test_side_stone_band_raw_watertight(raw_validate, a_dia, a_height, a_count, a_gap):
    """Across the curated in-range side_stone band each `compose(spec)` is a
    single watertight body on raw geometry."""
    spec = _side_stone_spec(
        a_dia=a_dia, a_height=a_height, a_count=a_count, a_gap=a_gap,
    )
    s = compose(spec)
    label = f"side_stone(dia={a_dia}, h={a_height}, n={a_count}, gap={a_gap})"
    assert len(s.solids()) == 1, f"{label}: expected one B-rep body"
    assert s.volume > 0, f"{label}: non-positive B-rep volume"
    _assert_castable(raw_validate(s), label)


# ------------------------------------------------------------- side floors
@pytest.mark.parametrize("a_dia,a_height,a_count,a_gap", BAND)
def test_side_stone_floors_hold(a_dia, a_height, a_count, a_gap):
    """Across the in-range band, the channel cut leaves both walls and the
    groove floor above MIN_WALL, via `check_side_stone` (the side_stone
    module's `_check`, which after CP3 measures the CUT, not the metal)."""
    spec = _side_stone_spec(
        a_dia=a_dia, a_height=a_height, a_count=a_count, a_gap=a_gap,
    )
    c = clamps(spec)
    from ringcad.geometry.side_stone import side_stone as _build
    solid = _build(spec, c)
    violations = MODULES["side_stone"].check(solid, spec, c)
    assert violations == [], (
        f"side_stone(dia={a_dia}, h={a_height}, n={a_count}) flagged: {violations}"
    )


def test_check_side_stone_ignores_non_side_stone_spec():
    """`check_side_stone` returns [] for a spec with no `side_stone` group
    (e.g. a plain SolitaireSpec routed through the same module.check call
    shape)."""
    from ringcad.geometry._castability import check_side_stone
    spec = from_params(CANONICAL_PARAMS)
    assert check_side_stone(object(), spec, clamps(spec)) == []


# ------------------------------------------------------------- placement
def test_accent_angles_are_symmetric():
    """The two shoulders' accent angles are mirror images (opposite sign)
    around the same shoulder start -- a sanity check on Decision 6's angle
    formula before it drives geometry."""
    spec = _side_stone_spec()
    c = clamps(spec)
    left = _accent_angles(spec, c, -1.0)
    right = _accent_angles(spec, c, 1.0)
    assert len(left) == len(right) == 3
    assert all(a < 0 for a in left)
    assert all(a > 0 for a in right)
    assert [abs(a) for a in left] == [abs(a) for a in right]


def test_stone_cuts_sit_at_the_same_radius():
    """Every stone cut on a shoulder sits at the same distance from the ring
    (finger) axis -- the row marches around the band at one depth, so the
    channel has a level floor rather than stones sinking into it."""
    spec = _side_stone_spec()
    c = clamps(spec)
    from ringcad.geometry.side_stone import _stone_cut
    radii = set()
    for angle in _accent_angles(spec, c, 1.0):
        bb = _stone_cut(spec, c, angle).bounding_box()
        cx = (bb.min.X + bb.max.X) / 2
        cy = (bb.min.Y + bb.max.Y) / 2
        radii.add(round((cx**2 + cy**2) ** 0.5, 4))
    assert len(radii) == 1


def test_trench_span_covers_the_accent_row():
    """The trench for a shoulder spans every accent's angle on that shoulder,
    with margin past the first/last -- otherwise an end stone is cut through a
    wall that the groove never reached."""
    spec = _side_stone_spec()
    c = clamps(spec)
    angles = _accent_angles(spec, c, 1.0)
    lo, hi = _trench_span(spec, c, 1.0)
    assert lo < min(angles)
    assert hi > max(angles)
