"""RNG-9 CP3 — halo composition watertight-by-construction (RED).

CP3-3 / CP3-4: the `halo` module rings N accent seats + N shared prongs on a
`gallery` and fuses them into ONE body; `compose(halo_spec)` then fuses that onto
the center setting for a SINGLE watertight castable halo — no floating ring. The
golden halo and a curated in-range band must each be a single watertight manifold
on RAW geometry (RNG-17 bar: NO `validate_and_repair`).

These FAIL today with an ImportError because `ringcad.geometry.halo` does not
exist yet — that missing feature is the RED signal, not a broken test. Per the
RNG-17 reframing, `.solids() == 1` + positive B-rep volume is asserted BEFORE
`raw_validate` (tests/conftest.py routes through `to_stl_bytes` WITHOUT repair).
"""
from __future__ import annotations

import math

import pytest

from ringcad.geometry import compose
from ringcad.geometry._common import clamps
from ringcad.geometry.halo import halo
from ringcad.geometry.outline import RoundOutline
from ringcad.ringspec import Halo, HaloSpec, Setting, Shank, Stones

# Curated CASTABLE band: min/mid/max of each halo dimension in representative
# combos crossed with two center configs. Deliberately EXCLUDES the overcrowded
# corner (count 24 + diameter 2.5 + gap 0.3, which CP1 already flags); the two
# dense (count=24) rows use the wider center stone so their arc spacing clears.
# (h_dia, h_count, h_gap, h_height, stone_dia, setting_h)
BAND = [
    (0.9, 8, 0.3, 0.8, 6.5, 3.0),    # small accents, sparse, low setting
    (1.3, 14, 0.5, 1.2, 6.5, 6.0),   # golden
    (2.5, 8, 1.5, 3.0, 10.0, 6.0),   # big accents, wide gap, sparse
    (1.3, 24, 0.5, 1.2, 10.0, 6.0),  # dense, mid diameter, wide center
    (0.9, 24, 0.3, 0.8, 10.0, 3.0),  # dense small accents, wide center
    (2.5, 14, 1.5, 3.0, 6.5, 3.0),   # big accents, mid count
    (1.3, 8, 1.5, 0.8, 6.5, 6.0),
    (0.9, 14, 0.5, 3.0, 10.0, 3.0),
]


def _halo_spec(*, h_dia=1.3, h_count=14, h_gap=0.5, h_height=1.2,
               stone_dia=6.5, setting_h=6.0):
    """The golden halo (solitaire defaults + halo defaults), field-overridable."""
    return HaloSpec(
        shank=Shank(inner_diameter=16.5, band_width=2.2, band_thickness=1.9),
        setting=Setting(prong_count=6, setting_height=setting_h),
        stones=Stones(stone_diameter=stone_dia, stone_height=4.0),
        halo=Halo(halo_stone_diameter=h_dia, halo_stone_count=h_count,
                  halo_gap=h_gap, halo_stone_height=h_height),
    )


def _assert_castable(result, label: str) -> None:
    assert result.body_count == 1, (
        f"{label}: body_count={result.body_count} (want 1)"
    )
    assert result.non_manifold_edges == 0, (
        f"{label}: non_manifold_edges={result.non_manifold_edges} (want 0)"
    )
    assert result.is_watertight, f"{label}: raw mesh is not watertight"


def test_halo_module_single_body():
    """CP3-3: the halo module alone (accent ring + shared prongs on the gallery)
    fuses to a single positive-volume body — the fast loop before full compose."""
    spec = _halo_spec()
    solid = halo(spec, clamps(spec))
    assert len(solid.solids()) == 1, "halo module did not fuse to one body"
    assert solid.volume > 0, "halo module has non-positive volume"


def test_golden_halo_single_watertight(raw_validate):
    """CP3-3: the raw golden `compose(halo_spec)` is a single watertight manifold
    — asserted WITHOUT validate_and_repair; the gallery makes it one body, so no
    floating ring. `.solids() == 1` + volume first, then the raw watertight bar."""
    spec = _halo_spec()
    s = compose(spec)
    assert len(s.solids()) == 1, "composed golden halo is not a single B-rep body"
    assert s.volume > 0, "composed golden halo has non-positive volume"
    _assert_castable(raw_validate(s), "golden halo compose")


@pytest.mark.parametrize("h_dia,h_count,h_gap,h_height,stone_dia,setting_h", BAND)
def test_halo_band_raw_watertight(
    raw_validate, h_dia, h_count, h_gap, h_height, stone_dia, setting_h
):
    """CP3-4: across the curated in-range halo band each `compose(halo_spec)` is a
    single watertight body on raw geometry."""
    spec = _halo_spec(h_dia=h_dia, h_count=h_count, h_gap=h_gap,
                      h_height=h_height, stone_dia=stone_dia, setting_h=setting_h)
    s = compose(spec)
    label = (f"halo(dia={h_dia}, n={h_count}, gap={h_gap}, h={h_height}, "
             f"sd={stone_dia}, gh={setting_h})")
    assert len(s.solids()) == 1, f"{label}: expected one B-rep body"
    assert s.volume > 0, f"{label}: non-positive B-rep volume"
    _assert_castable(raw_validate(s), label)


@pytest.mark.parametrize("n", [8, 9, 14, 24])
def test_ring_closes_and_count(n):
    """CP3-2: N seat angles + N midpoint prong angles, and the ring CLOSES — the
    last shared prong sits at the midpoint between accent N-1 and accent 0
    (wrap). Covers odd (9) and even parity.

    RNG-23 moved this contract from halo's private `_ring_angles` onto the stone
    outline (`angles_by_arc`), so that an oval halo can space its accents by arc
    length instead of by angle. On a circle the two coincide, so the contract
    asserted here is unchanged — only its home moved."""
    ring = RoundOutline(3.25)
    seats = ring.angles_by_arc(n)
    prongs = ring.angles_by_arc(n, offset=0.5)
    assert len(seats) == n, f"expected {n} seat angles, got {len(seats)}"
    assert len(prongs) == n, f"expected {n} prong angles, got {len(prongs)}"
    # each prong bisects an accent gap; the first between accent 0 and accent 1
    assert abs(prongs[0] - (seats[0] + seats[1]) / 2) < 1e-9
    # the last prong bisects accent N-1 and accent 0 (wrapped to +2*pi)
    expected_last = (seats[-1] + 2 * math.pi) / 2
    assert abs(prongs[-1] - expected_last) < 1e-9, "ring does not close at wrap"
