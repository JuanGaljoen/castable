"""7-param dict <-> RingSpec adapters (RNG-14, AC1).

Bridges the legacy flat 7-key params dict (ringcad.params) and the structured
RingSpec, additively — `/generate-ring` keeps using params until the RNG-15
cutover. The round-trip is lossless: `to_params(from_params(p)) == p` exactly
for every schema-valid input, ints stay ints. The 8th SCAD shaping param
`shank_taper` lives in the shank group; `to_params` drops it and `from_params`
restores its default, so the 7-key dict stays clean.
"""
from __future__ import annotations

from .models import RingSpec, Setting, Shank, SolitaireSpec, Stones

# Canonical 7-key order the round-trip preserves (matches params.PARAM_TYPES).
PARAM_KEYS = (
    "inner_diameter",
    "band_width",
    "band_thickness",
    "stone_diameter",
    "stone_height",
    "prong_count",
    "setting_height",
)

DEFAULT_SHANK_TAPER = 1.7


def from_params(p: dict) -> SolitaireSpec:
    """Map a flat 7-key params dict into a SolitaireSpec (shank_taper defaulted)."""
    return SolitaireSpec(
        shank=Shank(
            inner_diameter=p["inner_diameter"],
            band_width=p["band_width"],
            band_thickness=p["band_thickness"],
            shank_taper=DEFAULT_SHANK_TAPER,
        ),
        setting=Setting(
            prong_count=p["prong_count"],
            setting_height=p["setting_height"],
        ),
        stones=Stones(
            stone_diameter=p["stone_diameter"],
            stone_height=p["stone_height"],
        ),
    )


def to_params(spec: RingSpec) -> dict:
    """Flatten a RingSpec back to the canonical 7-key dict (drops shank_taper)."""
    values = {
        "inner_diameter": spec.shank.inner_diameter,
        "band_width": spec.shank.band_width,
        "band_thickness": spec.shank.band_thickness,
        "stone_diameter": spec.stones.stone_diameter,
        "stone_height": spec.stones.stone_height,
        "prong_count": int(spec.setting.prong_count),
        "setting_height": spec.setting.setting_height,
    }
    return {key: values[key] for key in PARAM_KEYS}
