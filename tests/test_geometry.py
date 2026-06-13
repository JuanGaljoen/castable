"""Geometry tests for scad/solitaire.scad (RNG-1).

Renders the parametric template headless via OpenSCAD across a matrix of
representative parameter sets and validates each mesh is castable. This is the
reusable "render -> validate" loop RNG-2 and RNG-5 build on.
"""
import math
from pathlib import Path

import pytest

from ringcad.render import render_scad, openscad_available
from ringcad.mesh_validator import validate_mesh, MIN_WALL_MM

SCAD = Path(__file__).resolve().parents[1] / "scad" / "solitaire.scad"

RENDER_TIMEOUT = 120         # hard kill (s)
# AC9: per-render budget. Generous for now — RNG-1 prioritises castable-quality
# geometry over speed; tighten (lower $fn / simplify) later if backend latency
# matters. Tracks the actual cost of the high-quality setting at $fn=64.
RENDER_BUDGET_S = 90
MAX_STL_BYTES = 50 * 1024 * 1024
MIN_STL_BYTES = 1024

DEFAULTS = dict(
    inner_diameter=17, band_width=4, band_thickness=1.6,
    stone_diameter=6.5, stone_height=4, prong_count=4, setting_height=4,
)

pytestmark = pytest.mark.skipif(
    not openscad_available(), reason="openscad not on PATH"
)


def _render(tmp_path, name, **overrides):
    params = {**DEFAULTS, **overrides}
    res = render_scad(SCAD, tmp_path / f"{name}.stl", params=params,
                      timeout=RENDER_TIMEOUT)
    assert res.returncode == 0, f"render failed:\n{res.stderr}"
    assert res.size_bytes > MIN_STL_BYTES
    return res


# ---- AC10: golden default ring (pure defaults, no -D overrides) ------------
def test_default_ring_renders_and_is_castable(tmp_path):
    res = render_scad(SCAD, tmp_path / "ring.stl", params=None,
                      timeout=RENDER_TIMEOUT)
    assert res.returncode == 0, res.stderr
    assert res.size_bytes > MIN_STL_BYTES
    v = validate_mesh(res.stl_path)
    assert v.is_castable, v


# ---- AC1: four modules union into one connected solid ----------------------
def test_assembly_is_single_body(tmp_path):
    res = _render(tmp_path, "single")
    v = validate_mesh(res.stl_path)
    assert v.body_count == 1
    assert v.is_watertight
    assert v.non_manifold_edges == 0


# ---- AC8 + AC9: parameter sweep, all castable + within budget --------------
SWEEP = [
    ("p4_average", dict(prong_count=4)),
    ("p6_average", dict(prong_count=6)),
    ("child_small", dict(inner_diameter=14, band_width=3, stone_diameter=4)),
    ("large_finger", dict(inner_diameter=23, band_width=6, stone_diameter=8)),
    ("thin_band", dict(band_thickness=0.9)),
    ("thick_band", dict(band_thickness=3.0)),
    ("oversized_stone", dict(stone_diameter=18)),
]


@pytest.mark.parametrize("name,ov", SWEEP, ids=[c[0] for c in SWEEP])
def test_sweep_castable_and_within_budget(tmp_path, name, ov):
    res = _render(tmp_path, name, **ov)
    assert res.seconds < RENDER_BUDGET_S, f"{name} too slow: {res.seconds:.1f}s"
    assert res.size_bytes < MAX_STL_BYTES
    v = validate_mesh(res.stl_path)
    assert v.is_castable, f"{name}: {v}"


# ---- AC2: parameters are wired through -D and change geometry ---------------
def test_inner_diameter_override_changes_geometry(tmp_path):
    small = validate_mesh(_render(tmp_path, "id14", inner_diameter=14).stl_path)
    large = validate_mesh(_render(tmp_path, "id22", inner_diameter=22).stl_path)
    # bigger finger hole -> larger overall extent and volume
    assert large.volume_mm3 > small.volume_mm3


# ---- AC3: band thickness clamped to min wall by construction ----------------
def test_band_thickness_clamped_to_min_wall(tmp_path):
    res = _render(tmp_path, "thinband", band_thickness=0.3)
    v = validate_mesh(res.stl_path)
    inner_r = DEFAULTS["inner_diameter"] / 2
    # the setting sits on +X, so the -X extent is the bare band outer radius
    outer_r = -v.bounds[0][0]
    assert outer_r - inner_r >= MIN_WALL_MM - 0.05, (
        f"band wall {outer_r - inner_r:.3f} < {MIN_WALL_MM}")
    assert v.is_castable


# ---- AC4: min prong tip enforced by construction (source guard) ------------
def test_scad_enforces_casting_constants():
    src = SCAD.read_text()
    assert "MIN_WALL" in src and "0.8" in src
    assert "MIN_PRONG_TIP" in src and "0.7" in src
    assert "max(" in src  # clamps present


# ---- AC1 + structure: modules + union present in source --------------------
def test_scad_defines_required_modules():
    src = SCAD.read_text()
    for module in ("shank(", "gallery(", "prongs(", "seat("):
        assert f"module {module}" in src, f"missing module {module}"
    assert "union()" in src


# ---- AC5: prong_count snaps to 4 + warns; equivalent to a real 4-prong -----
def test_prong_count_snaps_to_four_and_warns(tmp_path):
    five = _render(tmp_path, "p5", prong_count=5)
    assert "prong_count" in five.stderr.lower()
    assert "WARNING" in five.stderr.upper()
    v5 = validate_mesh(five.stl_path)
    v4 = validate_mesh(_render(tmp_path, "p4", prong_count=4).stl_path)
    v6 = validate_mesh(_render(tmp_path, "p6", prong_count=6).stl_path)
    # snapped-to-4 must be geometrically identical to a real 4-prong ring
    assert math.isclose(v5.volume_mm3, v4.volume_mm3, rel_tol=1e-4), \
        "snapped-to-4 should match a real 4-prong ring"
    # a 6-prong ring has two extra prongs -> measurably more volume (prongs are
    # small vs the whole ring, so compare by absolute volume, not ratio)
    assert v6.volume_mm3 - v4.volume_mm3 > 2.0, \
        "6-prong ring should have measurably more volume than 4-prong"


# ---- AC6: oversized stone warns but still renders valid geometry -----------
def test_oversized_stone_warns_and_is_valid(tmp_path):
    res = _render(tmp_path, "huge", stone_diameter=20)
    assert "stone" in res.stderr.lower()
    assert "WARNING" in res.stderr.upper()
    assert validate_mesh(res.stl_path).is_castable


# ---- AC11: clamp/snap warnings are emitted on stderr -----------------------
def test_warnings_go_to_stderr(tmp_path):
    res = _render(tmp_path, "warns", prong_count=7, stone_diameter=20)
    assert res.stderr.strip() != ""
    assert "WARNING" in res.stderr.upper()
