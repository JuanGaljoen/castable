"""RNG-19 CP2 — claws taper to a domed tip instead of bulging (RED).

`prong_setting` built each claw as spheres of near-constant `wire_r` joined by
cones, and capped it with a sphere of `tip_r * 1.45` — a node BIGGER than the
shaft below it. The claw therefore read as bent wire with a ball stuck on the
end, and was widest at exactly the point a real claw is narrowest. Measured
cross-sections up one claw's length told the story before any fix:

    10% 4.58mm2 · 40% 4.18 · 70% 3.80 · 90% 4.71 · 99% 6.32

— tapering properly, then ballooning over the last third.

Real cast claws taper continuously from base to tip and finish in a dome roughly
the shaft's own width (docs/jewelry-design-principles.md). Note our claw DIAMETER
is already correct trade practice at ~1.0mm, so this is a shape fix, not a sizing
one: nothing here should make the claws thicker.

Measured with the B-rep kernel rather than on a mesh. `solid & Plane(...)` gives
the exact cross-section area, where a mesh section would need `shapely` (not a
dependency) and would only approximate curved claw walls anyway. `placement()`
lays the local +Z setting frame onto the global +X head axis, so local height `z`
is the plane `x = (head_r - HEAD_INSET) + z`. Above the girdle the only material
is claw, so the area at a height reads directly on claw thickness there.
"""
from __future__ import annotations

import pytest
from build123d import Plane

from ringcad.geometry import prong_setting
from ringcad.geometry._common import HEAD_INSET, clamps
from ringcad.mesh_validator import MIN_PRONG_TIP_MM
from ringcad.ringspec import from_params

CANONICAL_PARAMS = {
    "inner_diameter": 16.5,
    "band_width": 2.2,
    "band_thickness": 1.9,
    "stone_diameter": 6.5,
    "stone_height": 4.0,
    "prong_count": 6,
    "setting_height": 6.0,
}


@pytest.fixture
def spec():
    return from_params(CANONICAL_PARAMS)


@pytest.fixture
def solid(spec):
    return prong_setting(spec)


def _area_at_local_z(solid, c, z: float) -> float:
    """Exact cross-sectional area of the claws at local height `z`."""
    section = solid & Plane(origin=(c["head_r"] - HEAD_INSET + z, 0, 0),
                            z_dir=(1, 0, 0))
    return float(section.area)


def _areas_up_the_claw(solid, c, fractions) -> list[float]:
    ring_z, rise = c["ring_z"], c["claw_rise"]
    return [_area_at_local_z(solid, c, ring_z + f * rise) for f in fractions]


def test_claws_are_narrowest_at_the_tip(spec, solid):
    c = clamps(spec)
    low, high = _areas_up_the_claw(solid, c, (0.10, 0.99))
    assert high < low, (
        f"claw cross-section is {high:.3f}mm2 at the tip against {low:.3f}mm2 "
        "near the base — the claw is widest at its tip, which is a ball on a "
        "stick, not a tapered cast claw"
    )


def test_claw_tapers_continuously_up_its_length(spec, solid):
    """Not merely narrower at the top: every step up should shed material."""
    c = clamps(spec)
    fractions = (0.10, 0.40, 0.70, 0.90, 0.99)
    areas = _areas_up_the_claw(solid, c, fractions)
    assert all(b < a for a, b in zip(areas, areas[1:])), (
        "claw cross-sections up the length are "
        f"{[round(a, 3) for a in areas]} at {fractions} of the rise — not "
        "monotonically decreasing, so the claw does not taper"
    )


def test_claw_tip_still_clears_the_casting_floor(spec, solid):
    """Tapering must not thin the tip past what lost-wax casting can hold."""
    c = clamps(spec)
    n = int(c["prong_n"])
    tip_area = _areas_up_the_claw(solid, c, (0.99,))[0]
    floor = n * 3.14159 * (MIN_PRONG_TIP_MM / 2) ** 2
    assert tip_area >= floor, (
        f"claw tips total {tip_area:.3f}mm2, under the {floor:.3f}mm2 implied by "
        f"{n} prongs at the {MIN_PRONG_TIP_MM}mm minimum tip diameter"
    )


def test_accent_prong_shaft_tapers_to_its_tip():
    """The accent prong (halo shared-prongs, trilogy side settings) was a
    straight `Cylinder` with a dome stuck on top — the small-scale version of
    the same defect. Authored in a local +Z frame, so an identity `loc` lets the
    section planes be plain horizontal cuts."""
    from build123d import Location

    from ringcad.geometry.accent_prong import accent_prong

    height = 1.6
    prong = accent_prong(accent_r=2.5, height=height, loc=Location())
    areas = [
        float((prong & Plane(origin=(0, 0, height * f), z_dir=(0, 0, 1))).area)
        for f in (0.1, 0.5, 0.85)
    ]
    assert all(b < a for a, b in zip(areas, areas[1:])), (
        f"accent-prong cross-sections are {[round(a, 4) for a in areas]} up its "
        "height — the shaft does not taper"
    )


def test_accent_prong_tip_still_clears_the_casting_floor():
    from build123d import Location

    from ringcad.geometry.accent_prong import accent_prong

    height = 1.6
    prong = accent_prong(accent_r=2.5, height=height, loc=Location())
    tip = float((prong & Plane(origin=(0, 0, height * 0.85), z_dir=(0, 0, 1))).area)
    floor = 3.14159 * (MIN_PRONG_TIP_MM / 2) ** 2
    assert tip >= floor * 0.95, (
        f"accent-prong tip {tip:.4f}mm2 is under the {floor:.4f}mm2 implied by "
        f"the {MIN_PRONG_TIP_MM}mm minimum tip diameter"
    )


def test_claws_are_not_made_thicker(spec, solid):
    """The trade diameter (~1.0mm) was already right. Guard against 'fixing' the
    look by adding metal: the base cross-section must not grow."""
    c = clamps(spec)
    n = int(c["prong_n"])
    base_area = _areas_up_the_claw(solid, c, (0.10,))[0]
    # 4.58mm2 over 6 claws was the pre-CP2 base; allow no meaningful growth.
    assert base_area <= 4.70, (
        f"claw base cross-section {base_area:.3f}mm2 over {n} claws has grown — "
        "CP2 is a shape fix, not a sizing one"
    )
