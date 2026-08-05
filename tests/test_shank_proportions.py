"""RNG-19 CP1 — the shank tapers in WIDTH, not in thickness (RED).

`docs/jewelry-design-principles.md`: real shanks taper in width toward the head
while thickness stays near-constant, so the ring keeps a consistent feel on the
finger. `_band_section` applied one `taper` factor to BOTH axes, making the band
3.4mm wide *and* 3.06mm thick at the head on the canonical spec — a swollen tube
rather than a shank rising to a head.

Asserted through the public `shank()` seam on the built solid's bounding box, not
against `_band_section`:

* the band is thickest at the head (+X) and thinnest opposite it (-X), so the two
  radial thicknesses come straight off `bbox.max.X` / `bbox.min.X`;
* width runs along global Z (`_band_section` puts the ellipse's second semi-axis
  on the plane's -Z), so the Z extent is the width at its widest point, the head.

The third test is the coupling guard. `placement()` anchors every setting at
`head_r - 0.4`, and `head_r` is derived from the thickness taper. Change the
thickness profile without changing `head_r` and every archetype's setting floats
clear of the band it is supposed to be welded into — watertight by construction
would break silently at the fuse.
"""
from __future__ import annotations

import pytest

from ringcad.geometry import shank
from ringcad.geometry._common import clamps
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

# A shank whose thickness varies by more than this around the ring reads as a
# swollen tube. Not zero: a slight rise into the head is real jewelry practice
# and carries the setting.
THICKNESS_DRIFT_TOL_MM = 0.35
# The head must still be visibly wider than the back, or there is no taper left.
MIN_WIDTH_FLARE = 1.10


@pytest.fixture
def spec():
    return from_params(CANONICAL_PARAMS)


@pytest.fixture
def box(spec):
    return shank(spec).bounding_box()


def test_band_thickness_is_near_constant_around_the_ring(spec, box):
    inner_r = clamps(spec)["inner_r"]
    th_head = box.max.X - inner_r
    th_back = abs(box.min.X) - inner_r
    assert abs(th_head - th_back) <= THICKNESS_DRIFT_TOL_MM, (
        f"thickness at head {th_head:.3f}mm vs back {th_back:.3f}mm "
        f"(drift {abs(th_head - th_back):.3f} > {THICKNESS_DRIFT_TOL_MM}) — "
        "the band tapers in thickness, which real shanks do not"
    )


def test_band_width_still_flares_toward_the_head(spec, box):
    bw = clamps(spec)["bw"]
    assert box.size.Z >= bw * MIN_WIDTH_FLARE, (
        f"widest width {box.size.Z:.3f}mm is not {MIN_WIDTH_FLARE}x the nominal "
        f"{bw:.3f}mm — the width taper has been flattened away"
    )


def test_head_r_matches_the_real_band_surface_at_the_head(spec, box):
    """`placement()` welds every setting at `head_r - 0.4`; if `head_r` drifts
    from the band's true outer radius the setting floats (or buries)."""
    head_r = clamps(spec)["head_r"]
    assert head_r == pytest.approx(box.max.X, abs=0.05), (
        f"head_r {head_r:.3f}mm != band outer radius at head {box.max.X:.3f}mm — "
        "settings would not be welded into the band surface"
    )
