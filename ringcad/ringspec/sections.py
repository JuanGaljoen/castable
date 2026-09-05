"""SectionProfile — the shank's cross-section, as two independent axes (RNG-25).

**Kernel-free by design**, mirroring `cuts.py`'s split for the centre stone:
this module imports no `build123d`, so `ringcad.ringspec.castability` and
`ringcad.geometry._common` read the same facts instead of each deriving them
(docs/adr/0002) -- spec layer owns the section FACTS, geometry layer owns the
kernel CONSTRUCTION (the seat/wire it becomes).

Research (docs/research/shank-cross-section-profiles.md) found the trade's own
names are a 2x2 of two independent choices, not one list of four: "comfort fit"
is purely a domed INNER surface, and the trade pairs it with every outer shape
independently (Stuller stocks "Half Round Comfort Fit" and "Comfort-Fit Heavy
Knife Edge" as separate SKUs). So `outer_profile` and `inner_profile` compose
rather than enumerate.

Coordinate convention: `s` runs across the band from -1 to +1 (one edge to the
other; s=0 is the centreline). `outer(s)`/`inner(s)` return the surface's
offset from the band's inner radius, in units of `th` -- the section's
thickness AT THE CENTRELINE. The actual band radius at a given `s` is then
`inner_r + th * outer(s)` (outer surface) or `inner_r + th * inner(s)` (inner
surface); `geometry/_common.py` (CP2) is what turns that into a build123d face.

**`domed` + `domed` is `court`** -- today's `Ellipse(th/2, w/2)`, reproduced
exactly (see `test_domed_domed_reproduces_the_current_ellipse`), so every spec
written before RNG-25 renders identically once both fields default to it.
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Callable

OUTER_NAMES: tuple[str, ...] = ("domed", "flat", "knife_edge")
INNER_NAMES: tuple[str, ...] = ("domed", "flat")


def _inner_flat(s: float) -> float:
    return 0.0


def _inner_domed(s: float) -> float:
    return 0.5 * (1 - math.sqrt(max(0.0, 1 - s * s)))


def _outer_flat(s: float) -> float:
    return 1.0


def _outer_domed(s: float) -> float:
    return 0.5 * (1 + math.sqrt(max(0.0, 1 - s * s)))


_INNER: dict[str, Callable[[float], float]] = {
    "domed": _inner_domed,
    "flat": _inner_flat,
}

_OUTER_SIMPLE: dict[str, Callable[[float], float]] = {
    "domed": _outer_domed,
    "flat": _outer_flat,
}


@dataclass(frozen=True)
class SectionProfile:
    """One outer x inner combination. Sized on demand, like `CutProfile`:
    nothing here is band-specific until `outer`/`inner` are called with `s`."""

    outer_profile: str
    inner_profile: str

    def inner(self, s: float) -> float:
        return _INNER[self.inner_profile](s)

    def outer(self, s: float, apex_fraction: float = 1.0) -> float:
        """`apex_fraction` (`a`) is the knife edge's flat-crown half-width in
        `s`; every other outer profile ignores it. Every profile returns
        exactly 1.0 at `s=0` by construction -- see `head_r` below."""
        if self.outer_profile == "knife_edge":
            a = min(apex_fraction, 1.0)
            return 1.0 if abs(s) <= a else (1 - abs(s)) / (1 - a)
        return _OUTER_SIMPLE[self.outer_profile](s)


def section_for(outer_profile: str, inner_profile: str) -> SectionProfile:
    """The `SectionProfile` for a RingSpec `shank.outer_profile`/`inner_profile`."""
    if outer_profile not in OUTER_NAMES:
        raise ValueError(
            f"unknown outer_profile {outer_profile!r}; supported: "
            f"{', '.join(OUTER_NAMES)}"
        )
    if inner_profile not in INNER_NAMES:
        raise ValueError(
            f"unknown inner_profile {inner_profile!r}; supported: "
            f"{', '.join(INNER_NAMES)}"
        )
    return SectionProfile(outer_profile, inner_profile)


def knife_edge_apex_fraction(band_width: float, min_wall: float) -> float:
    """`a` in [0, 1]: the flat crown's half-width in `s`, sized so the crown is
    exactly `min_wall` wide across the band -- castable BY CONSTRUCTION (the
    RNG-17 bar), not a gate rule. `a -> 1` as `band_width -> min_wall`: the
    knife edge degenerates smoothly into a flat band rather than being
    rejected, since no source publishes a "how knife-edge is knife-edge
    enough" threshold to reject it against (specs/RNG-25.md)."""
    return min(1.0, min_wall / band_width) if band_width > 0 else 1.0


def head_r(inner_r: float, bt: float, t_taper: float,
           profile: SectionProfile) -> float:
    """The band's outer radius at the head, so every setting welds into metal
    rather than balancing on it (`geometry/_common.placement`).

    Every profile reaches full thickness `bt * t_taper` at the centreline
    (`profile.outer(0) == 1`, whatever the outer profile), so this value is
    the SAME for every profile. Deriving it here rather than as a bare
    `inner_r + bt * t_taper` at each call site is what keeps the builder and
    the castability check from drifting apart when the profile changes
    (docs/adr/0002) -- the same failure that already hit `shank_taper` once.
    """
    return inner_r + bt * t_taper * profile.outer(0.0)
