"""RNG-25 CP2 — the shank cross-section, six profiles, through `compose()`.

Court (the pre-RNG-25 default) must stay bit-identical to the golden STLs.
Every other profile must be a single raw watertight manifold with positive
volume (the RNG-17 bar, ADR-0005's "assert volume and body count, not just
watertightness") -- asserted through the public `compose(spec)` seam, never
against `_band_section`/`section_face` internals.
"""
from __future__ import annotations

import pytest

from ringcad.geometry.export import to_stl_bytes
from ringcad.geometry.module import compose
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

PROFILES = [
    ("domed", "domed"),   # court -- today's default
    ("domed", "flat"),    # D-section
    ("flat", "domed"),    # flat court / comfort fit
    ("flat", "flat"),     # flat
    ("knife_edge", "flat"),    # knife-edge
    ("knife_edge", "domed"),   # comfort-fit knife-edge
]


def _spec(outer_profile, inner_profile):
    spec = from_params(CANONICAL_PARAMS)
    return spec.model_copy(
        update={
            "shank": spec.shank.model_copy(
                update={"outer_profile": outer_profile,
                        "inner_profile": inner_profile}
            )
        }
    )


def test_flat_profile_has_more_volume_than_court():
    """`flat` (a literal rectangle section) must have MORE material than
    `court` (a lens tapering to zero at the edges) for the same th/w -- the
    seam that pins `_band_section` actually reading the profile, rather than
    every profile silently building the same ellipse."""
    court = compose(_spec("domed", "domed"))
    flat = compose(_spec("flat", "flat"))
    assert flat.volume > court.volume * 1.2


def test_default_spec_is_bit_identical_to_pre_rng25_golden_stl():
    """Omitting both fields must reproduce today's geometry exactly -- the
    golden solitaire byte-for-byte, not just "close"."""
    before = to_stl_bytes(compose(from_params(CANONICAL_PARAMS)))
    after = to_stl_bytes(compose(_spec("domed", "domed")))
    assert after == before


@pytest.mark.parametrize("outer,inner", PROFILES)
def test_every_profile_is_single_watertight_positive_volume(
    raw_validate, outer, inner
):
    solid = compose(_spec(outer, inner))
    label = f"outer={outer} inner={inner}"
    assert len(solid.solids()) == 1, f"{label}: expected exactly one B-rep body"
    assert solid.volume > 0, f"{label}: non-positive B-rep volume"
    result = raw_validate(solid)
    assert result.body_count == 1, f"{label}: body_count={result.body_count}"
    assert result.non_manifold_edges == 0, (
        f"{label}: non_manifold_edges={result.non_manifold_edges}"
    )
    assert result.is_watertight, f"{label}: raw mesh is not watertight"
