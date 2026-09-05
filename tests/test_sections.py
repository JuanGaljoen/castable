"""SectionProfile — the shank cross-section as two independent axes (RNG-25).

Kernel-free, pure-function seam, mirroring `test_cut_outlines.py`'s relationship
to `cuts.py`. `outer(s)`/`inner(s)` return the surface offset from the band's
inner radius, in units of `th` (the thickness at the centreline, s=0); `s` runs
across the band from -1 (one edge) to +1 (the other).
"""
from __future__ import annotations

import math

import pytest

from ringcad.ringspec.sections import (
    INNER_NAMES, OUTER_NAMES, SectionProfile, head_r, knife_edge_apex_fraction,
    section_for,
)


def test_section_for_rejects_unknown_outer_profile():
    with pytest.raises(ValueError, match="outer_profile"):
        section_for("bulging", "domed")


def test_section_for_rejects_unknown_inner_profile():
    with pytest.raises(ValueError, match="inner_profile"):
        section_for("domed", "bulging")


def test_every_profile_reaches_full_thickness_at_mid_width():
    """`outer(0) == 1` for every outer profile -- the invariant that lets
    `head_r` be computed once and never move when the profile changes."""
    for outer in OUTER_NAMES:
        profile = section_for(outer, "domed")
        assert profile.outer(0.0, apex_fraction=0.3) == pytest.approx(1.0)


def test_inner_flat_is_zero_everywhere():
    profile = section_for("flat", "flat")
    for s in (-1.0, -0.5, 0.0, 0.5, 1.0):
        assert profile.inner(s) == pytest.approx(0.0)


def test_inner_domed_reaches_half_thickness_at_edges():
    """The dome rises from 0 at the centreline to 0.5 (half the section's
    thickness) at each edge -- the classic comfort-fit curve."""
    profile = section_for("flat", "domed")
    assert profile.inner(0.0) == pytest.approx(0.0)
    assert profile.inner(1.0) == pytest.approx(0.5)
    assert profile.inner(-1.0) == pytest.approx(0.5)


def test_outer_flat_is_full_thickness_everywhere():
    profile = section_for("flat", "flat")
    for s in (-1.0, -0.5, 0.0, 0.5, 1.0):
        assert profile.outer(s) == pytest.approx(1.0)


def test_domed_domed_reproduces_the_current_ellipse():
    """`domed`+`domed` is `court` -- today's `Ellipse(th/2, w/2)` -- so the
    section's thickness at any `s` must equal the ellipse's: `sqrt(1-s^2)`."""
    profile = section_for("domed", "domed")
    for s in (-1.0, -0.7, -0.3, 0.0, 0.3, 0.7, 1.0):
        thickness = profile.outer(s) - profile.inner(s)
        assert thickness == pytest.approx(math.sqrt(1 - s * s))


def test_knife_edge_flat_crown_within_apex_fraction():
    profile = section_for("knife_edge", "flat")
    a = 0.4
    assert profile.outer(0.0, apex_fraction=a) == pytest.approx(1.0)
    assert profile.outer(a, apex_fraction=a) == pytest.approx(1.0)
    assert profile.outer(-a, apex_fraction=a) == pytest.approx(1.0)


def test_knife_edge_tapers_to_zero_at_the_band_edge():
    profile = section_for("knife_edge", "flat")
    assert profile.outer(1.0, apex_fraction=0.4) == pytest.approx(0.0)
    assert profile.outer(-1.0, apex_fraction=0.4) == pytest.approx(0.0)


def test_knife_edge_apex_fraction_sizes_the_crown_to_min_wall():
    """`a = min_wall / band_width` gives a flat crown exactly `min_wall` wide
    across the band, regardless of `band_width` -- the by-construction floor,
    not a gate rule (specs/RNG-25.md)."""
    for band_width in (1.0, 2.0, 2.5, 5.0):
        a = knife_edge_apex_fraction(band_width, min_wall=0.8)
        crown_width_mm = a * band_width
        assert crown_width_mm == pytest.approx(0.8)


def test_knife_edge_apex_fraction_degenerates_to_flat_at_the_wall_floor():
    """As `band_width -> min_wall`, `a -> 1`: the whole section becomes crown,
    i.e. the knife edge degenerates into a flat band rather than being
    rejected -- no published "how sharp is knife-edge enough" threshold
    exists to reject it against (docs/research/shank-cross-section-profiles.md)."""
    a = knife_edge_apex_fraction(0.8, min_wall=0.8)
    assert a == pytest.approx(1.0)


def test_head_r_is_the_same_for_every_profile():
    """The band's outer radius at the head must not move when the profile
    changes -- every profile reaches full thickness at s=0 by construction,
    so `head_r` is one function, not a value each profile recomputes
    (docs/adr/0002)."""
    inner_r, bt, t_taper = 8.25, 1.9, 1.15
    baseline = head_r(inner_r, bt, t_taper, section_for("domed", "domed"))
    assert baseline == pytest.approx(inner_r + bt * t_taper)
    for outer in OUTER_NAMES:
        for inner in INNER_NAMES:
            profile = section_for(outer, inner)
            assert head_r(inner_r, bt, t_taper, profile) == pytest.approx(baseline)


def test_registry_names_are_exhaustive():
    assert set(OUTER_NAMES) == {"domed", "flat", "knife_edge"}
    assert set(INNER_NAMES) == {"domed", "flat"}
