"""RNG-14 AC1 — lossless 7-param round-trip through RingSpec.

RED until the `ringcad.ringspec` package exists: the import below fails at
collection (ModuleNotFoundError), which is the correct RED signal — the
feature (the package + adapters) is MISSING, not buggy.

AC1 contract: `from_params(p)` -> RingSpec -> `to_params()` returns the
identical 7 values for every schema-valid 7-param input (exact equality, ints
stay ints). The 8th SCAD shaping param `shank_taper` is dropped by `to_params`
and restored to its default by `from_params`, so the 7-key dict stays lossless.

Uses a stdlib `itertools.product` grid (NOT hypothesis — no new dependency).
"""
import itertools

import pytest

from ringcad.ringspec import from_params, to_params

# Canonical key order the 7-param dict must round-trip through unchanged.
CANONICAL_KEYS = [
    "inner_diameter",
    "band_width",
    "band_thickness",
    "stone_diameter",
    "stone_height",
    "prong_count",
    "setting_height",
]

# ~3 schema-valid values per field, comfortably inside the bounds. The
# band_thickness grid includes the 0.8mm boundary value on purpose (it is a
# valid spec — the castability floor is enforced elsewhere, not the schema).
GRID = {
    "inner_diameter": (14.0, 16.5, 20.0),
    "band_width": (1.8, 2.2, 3.0),
    "band_thickness": (0.8, 1.5, 2.5),
    "stone_diameter": (4.0, 6.5, 8.0),
    "stone_height": (3.0, 4.0, 5.0),
    "prong_count": (4, 6),
    "setting_height": (4.0, 6.0, 8.0),
}


def _all_param_dicts():
    """Cartesian product of the per-field grids -> one 7-key dict per combo."""
    keys = list(GRID.keys())
    for combo in itertools.product(*(GRID[k] for k in keys)):
        yield dict(zip(keys, combo))


ALL_PARAMS = list(_all_param_dicts())


# --- AC1: exact round-trip identity over the valid input space ---------------
@pytest.mark.parametrize("p", ALL_PARAMS)
def test_roundtrip_is_exact(p):
    out = to_params(from_params(p))
    assert out == p


@pytest.mark.parametrize("p", ALL_PARAMS)
def test_roundtrip_preserves_prong_count_int(p):
    out = to_params(from_params(p))
    # int-ness must survive the trip (not silently coerced to 4.0 / 6.0).
    assert type(out["prong_count"]) is int


# --- AC1: shank_taper is the dropped/restored 8th param ----------------------
def test_to_params_never_emits_shank_taper():
    for p in ALL_PARAMS:
        out = to_params(from_params(p))
        assert "shank_taper" not in out


def test_from_params_restores_default_shank_taper():
    spec = from_params(ALL_PARAMS[0])
    assert spec.shank.shank_taper == 1.7


# --- AC1: canonical key order ------------------------------------------------
def test_to_params_returns_keys_in_canonical_order():
    out = to_params(from_params(ALL_PARAMS[0]))
    assert list(out.keys()) == CANONICAL_KEYS
