"""RNG-15 AC2 — characterization parity for the build123d solitaire (RED).

RED until `ringcad.geometry` exists. Pins the OpenSCAD reference metrics as
constants (no `openscad` subprocess at test time — parity was proven in
RNG-13; git is the rollback) and asserts the in-process build123d output lands
within the RNG-13 tolerances: bbox ≤ 0.5mm/axis, volume ≤ 5%.

Also pins AC4's shipped-mesh contract: the raw build123d STL carries the
spike's boolean-tangency seams (~12 non-manifold edges), and
`ringcad.mesh_validator.validate_and_repair` welds them to a watertight,
zero-non-manifold-edge mesh with no meaningful volume change.
"""
from io import BytesIO

import pytest
import trimesh

from ringcad.geometry import build_solitaire, to_stl_bytes
from ringcad.mesh_validator import validate_and_repair, validate_mesh
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

# Characterization metrics for CANONICAL_PARAMS.
#
# REBASELINED in RNG-19 CP1 (2026-08-05). These were the OpenSCAD reference
# metrics carried since RNG-13; the shank now tapers in WIDTH only, with
# thickness near-constant (docs/jewelry-design-principles.md), so the geometry
# has deliberately diverged from the OpenSCAD original and parity against it is
# no longer the thing being characterized. What these constants pin from here on
# is "the solitaire has not changed shape UNINTENTIONALLY".
#
#   bbox   (27.795, 21.283, 7.500) -> (26.765, 20.501, 7.500)
#   volume  383.58                 ->  279.51 mm^3   (-27%)
#
# The X drop is the thinner head (band thickness at the head 3.23 -> 2.185mm);
# the volume drop is that plus the width flare easing from 1.7x to 1.35x. Both
# are the intended change, not a regression — the band was carrying metal a real
# shank would not.
REF_BBOX = (26.765, 20.501, 7.500)   # mm, (x, y, z) extents
REF_VOLUME_MM3 = 279.51              # mm^3

BBOX_TOL_MM = 0.5     # RNG-13: each axis within 0.5mm of the baseline
VOLUME_TOL = 0.05     # RNG-13: volume within 5%
REPAIR_VOLUME_TOL = 0.005  # repair welds seams; volume must barely move (<0.5%)


@pytest.fixture
def stl_bytes():
    return to_stl_bytes(build_solitaire(from_params(CANONICAL_PARAMS)))


def _mesh(data: bytes) -> trimesh.Trimesh:
    return trimesh.load(BytesIO(data), file_type="stl", force="mesh")


# --- AC2: bbox parity, per axis ----------------------------------------------
def test_bbox_within_half_mm_of_openscad(stl_bytes):
    extents = _mesh(stl_bytes).bounding_box.extents
    for axis, (got, ref) in enumerate(zip(extents, REF_BBOX)):
        assert abs(got - ref) <= BBOX_TOL_MM, (
            f"bbox axis {axis}: {got:.3f} vs ref {ref:.3f} "
            f"(Δ {abs(got - ref):.3f} > {BBOX_TOL_MM})"
        )


# --- AC2: volume parity ------------------------------------------------------
def test_volume_within_5pct_of_openscad(stl_bytes):
    vol = abs(_mesh(stl_bytes).volume)
    lo = REF_VOLUME_MM3 * (1 - VOLUME_TOL)
    hi = REF_VOLUME_MM3 * (1 + VOLUME_TOL)
    assert lo <= vol <= hi, f"volume {vol:.2f} outside ±5% of {REF_VOLUME_MM3}"


# --- AC4: repair welds raw seams to a clean, watertight manifold -------------
def test_validate_and_repair_yields_watertight_zero_nme(stl_bytes):
    outcome = validate_and_repair(stl_bytes)
    assert outcome.mesh_valid is True
    result = validate_mesh(_mesh(outcome.stl_bytes))
    assert result.is_watertight is True
    assert result.non_manifold_edges == 0


# --- AC4: repair preserves volume (welding seams, not reshaping) -------------
def test_repair_preserves_volume(stl_bytes):
    raw_vol = abs(_mesh(stl_bytes).volume)
    repaired = validate_and_repair(stl_bytes).stl_bytes
    repaired_vol = abs(_mesh(repaired).volume)
    assert raw_vol > 0
    assert abs(repaired_vol - raw_vol) <= raw_vol * REPAIR_VOLUME_TOL, (
        f"repair changed volume {raw_vol:.3f} -> {repaired_vol:.3f}"
    )
