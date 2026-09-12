"""RNG-24 — geometry identity across the archetype-union retirement.

RNG-24 changes DISPATCH (how a spec is validated and routed), not construction
(the build123d modules themselves are untouched), so every existing golden
spec must reproduce byte-identical STL after the refactor. These hashes were
captured on the pre-RNG-24 tree (the last commit before this ticket's CP1)
using the exact construction each golden test elsewhere in this suite already
uses (`from_params` for solitaire; `HaloSpec`/`TrilogySpec`/`SideStoneSpec`
at their own field defaults for the rest). A mismatch here is a dispatch bug
introduced by this ticket, not a criterion to relax (see specs/RNG-24.md).
"""
from __future__ import annotations

import hashlib

from ringcad.geometry.export import to_stl_bytes
from ringcad.geometry.module import compose
from ringcad.ringspec import (
    HaloSpec,
    Halo,
    SideStone,
    SideStoneSpec,
    Setting,
    Shank,
    Stones,
    Trilogy,
    TrilogySpec,
    from_params,
)

CANONICAL_PARAMS = {
    "inner_diameter": 16.5,
    "band_width": 2.2,
    "band_thickness": 1.9,
    "stone_diameter": 6.5,
    "stone_height": 4.0,
    "prong_count": 6,
    "setting_height": 6.0,
}

# sha256(to_stl_bytes(compose(spec))) captured pre-RNG-24, one per archetype.
GOLDEN_HASHES = {
    "solitaire": "bfa52e2c715dd8f49c6a5da785e2c14b07d1f834ef788c01a8fc7e34b913ebb5",
    "halo": "6ea0f221267e82bb47c96d1267d338a7caa565b20c64d2aa72d9704cd57e75a4",
    "trilogy": "a3fe7628081ef9077e5a41d01565d9e1daa0d83d3fa43b53d1e6d29932a0e744",
    "side_stone": "8f5531c3cacdf2cb3aec44932fce7e01e045968e6e367823d5f08950d3c4e226",
}


def _shank():
    return Shank(inner_diameter=16.5, band_width=2.2, band_thickness=1.9)


def _golden_specs():
    setting = Setting(prong_count=6, setting_height=6.0)
    stones = Stones(stone_diameter=6.5, stone_height=4.0)
    return {
        "solitaire": from_params(CANONICAL_PARAMS),
        "halo": HaloSpec(
            shank=_shank(), setting=setting, stones=stones, halo=Halo(),
        ),
        "trilogy": TrilogySpec(
            shank=_shank(), setting=setting, stones=stones, trilogy=Trilogy(),
        ),
        "side_stone": SideStoneSpec(
            shank=_shank(), setting=setting, stones=stones,
            side_stone=SideStone(),
        ),
    }


def test_golden_specs_are_byte_identical_across_the_union_retirement():
    for name, spec in _golden_specs().items():
        digest = hashlib.sha256(to_stl_bytes(compose(spec))).hexdigest()
        assert digest == GOLDEN_HASHES[name], (
            f"{name}: geometry changed by RNG-24's dispatch refactor "
            f"(got {digest})"
        )
