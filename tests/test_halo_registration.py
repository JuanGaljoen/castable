"""RNG-9 CP3 — halo registration + isolation + solitaire parity (RED).

CP3-2 / CP3-5: the halo composition registers as `MODULES["halo"]` and
`ARCHETYPES["halo"] = ["shank","seat","prong_setting","halo"]`; `compose(halo_spec)`
works, but the `/generate-ring` endpoint and frontend stay untouched (CP4). The
solitaire archetype and its composed geometry must be BYTE-FOR-INTENT unchanged.

These FAIL today with an ImportError because `ringcad.geometry.halo` does not
exist yet and `MODULES`/`ARCHETYPES` carry no "halo" entry — that missing
registration is the RED signal, not a broken test.
"""
from __future__ import annotations

from ringcad.geometry import compose
from ringcad.geometry._common import clamps
from ringcad.geometry.halo import halo
from ringcad.geometry.module import ARCHETYPES, MODULES
from ringcad.ringspec import Halo, HaloSpec, Setting, Shank, Stones, from_params

CANONICAL_PARAMS = {
    "inner_diameter": 16.5,
    "band_width": 2.2,
    "band_thickness": 1.9,
    "stone_diameter": 6.5,
    "stone_height": 4.0,
    "prong_count": 6,
    "setting_height": 6.0,
}

# Pre-CP3 solitaire baseline (RNG-16 compose target); parity must hold.
EXPECTED_VOLUME_MM3 = 389.56
VOLUME_TOL = 0.05   # +/-5%, the RNG-13 parity band


def _halo_spec():
    return HaloSpec(
        shank=Shank(inner_diameter=16.5, band_width=2.2, band_thickness=1.9),
        setting=Setting(prong_count=6, setting_height=6.0),
        stones=Stones(stone_diameter=6.5, stone_height=4.0),
        halo=Halo(),
    )


def _assert_castable(result, label: str) -> None:
    assert result.body_count == 1, (
        f"{label}: body_count={result.body_count} (want 1)"
    )
    assert result.non_manifold_edges == 0, (
        f"{label}: non_manifold_edges={result.non_manifold_edges} (want 0)"
    )
    assert result.is_watertight, f"{label}: raw mesh is not watertight"


def test_halo_registered():
    """CP3-2: halo is a registered composable module with the fixed archetype
    order, and its check returns a list."""
    assert "halo" in MODULES
    assert ARCHETYPES["halo"] == ["shank", "seat", "prong_setting", "halo"]
    spec = _halo_spec()
    c = clamps(spec)
    result = MODULES["halo"].check(halo(spec, c), spec, c)
    assert isinstance(result, list)


def test_solitaire_parity_unchanged(raw_validate):
    """CP3-5: adding halo leaves the solitaire archetype + its composed geometry
    unchanged — same module order, same volume within parity, still a single
    watertight body."""
    assert ARCHETYPES["solitaire"] == ["shank", "seat", "prong_setting"]
    s = compose(from_params(CANONICAL_PARAMS))
    rel = abs(s.volume - EXPECTED_VOLUME_MM3) / EXPECTED_VOLUME_MM3
    assert rel < VOLUME_TOL, f"solitaire volume drifted: {s.volume:.2f}mm^3"
    assert len(s.solids()) == 1, "solitaire is no longer a single body"
    _assert_castable(raw_validate(s), "solitaire parity")


def test_isolation_no_endpoint():
    """CP3-5: `compose(halo_spec)` succeeds at the module boundary; the endpoint
    and frontend are NOT wired (CP4). A light registration/compose assertion,
    not an HTTP call."""
    s = compose(_halo_spec())
    assert s.volume > 0
