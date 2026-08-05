"""RNG-19 CP1 — the trilogy's side settings must not splay off the finger (RED).

`_side_loc` rotated the ENTIRE setting frame by the angular offset, so each side
stone's table faced radially outward at that angle rather than roughly where the
centre stone's does. On a real photo-derived spec the offset is 51 degrees per
side, turning the two flanking heads into wings and making the ring wider ACROSS
the ring plane than the ring's own diameter.

Real three-stone rings read as one continuous line: the sides sit close to the
centre and their tables stay near-coplanar with it, tilting only gently with the
shoulder (docs/jewelry-design-principles.md).

Asserted on the composed solid's bounding box, a public seam:

* X is the head axis (the centre setting stands at +X);
* Y spans the ring plane perpendicular to it — the axis the three-stone row runs
  along, so it is exactly what "splay" shows up on;
* Z is the finger axis (band width).

`Y <= X` is the invariant: a ring may be as wide across as it is tall, but a
trilogy whose stone row overhangs its own diameter is splayed, not set.
"""
from __future__ import annotations

from io import BytesIO

import pytest
import trimesh

from ringcad.geometry import compose, to_stl_bytes
from ringcad.ringspec import validate_spec

# The real trilogy spec the fidelity corpus produced from a photo (RNG-22), with
# the 2.0mm side-stone gap that drives the 51-degree offset. Inlined rather than
# read from probes/output/, which is gitignored.
TRILOGY_SPEC = {
    "version": "1.0",
    "archetype": "trilogy",
    "shank": {"inner_diameter": 16.5, "band_width": 2.0, "band_thickness": 1.8},
    "setting": {"prong_count": 6, "setting_height": 7.5},
    "stones": {
        "stone_diameter": 8.0, "stone_height": 5.5,
        "shape": "oval", "length_ratio": 1.4,
    },
    "trilogy": {
        "side_stone_diameter": 5.0, "side_stone_gap": 2.0,
        "side_stone_height": 4.0,
    },
}


@pytest.fixture
def box():
    solid = compose(validate_spec(TRILOGY_SPEC))
    mesh = trimesh.load(BytesIO(to_stl_bytes(solid)), file_type="stl")
    return mesh.bounding_box.extents


def test_side_settings_do_not_overhang_the_ring(box):
    x, y, _ = (float(v) for v in box)
    assert y <= x, (
        f"trilogy spans {y:.2f}mm across the ring plane against a {x:.2f}mm "
        "head axis — the side settings splay off the finger instead of reading "
        "as one line of three stones"
    )


def test_trilogy_still_generates_a_single_watertight_solid():
    """The splay fix moves the side settings relative to their posts; the post
    must still plunge into the band, not graze it (the recurring OCCT trap)."""
    solid = compose(validate_spec(TRILOGY_SPEC))
    mesh = trimesh.load(BytesIO(to_stl_bytes(solid)), file_type="stl")
    assert mesh.is_watertight, "trilogy is no longer watertight by construction"
    # docs/adr/0005: a fuse that silently DROPS bodies still reports watertight.
    assert abs(mesh.volume) > 300.0, (
        f"volume {abs(mesh.volume):.1f}mm3 is too low for a trilogy — a fuse "
        "has probably dropped a body while still reporting watertight"
    )
