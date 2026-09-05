"""section_face() -- the shank cross-section as a build123d 2D face (RNG-25 CP2).

Kernel half of `ringcad.ringspec.sections`: the spec layer answers WHAT the
section is (`SectionProfile.outer`/`inner`, fraction-of-`th` offsets from the
band's inner radius); this module turns that into a face in the LOCAL setting
frame `_band_section` already builds at each ring angle (local x = radial/
thickness, local y = across-band/width -- the same frame the pre-RNG-25
`Ellipse(th/2, w/2)` call used).

**`court` (domed outer, domed inner) keeps that literal `Ellipse` call** --
bit-identical to every ring generated before RNG-25 (the `RoundOutline`
precedent: an exact primitive that's already right stays exact, rather than
being routed through general machinery for no gain).

Every other profile is built from EXACT pieces, never a sampled approximation
-- a flat run is a straight `Line`, a domed run is a genuine `EllipticalCenterArc`
half, and a knife edge is three straight `Line`s (the two slopes and the flat
crown). `outline.py`'s own docstring is the reason: "a sampled spline still
yields a closed, watertight wire that merely looks wrong" for a shape whose
identity is its straight edges and its crisp crown.

**Only the amplitude each side carries changes between combinations** -- the
shape family (line / half-ellipse / three-line knife) is fixed per profile
name, and `sections.SectionProfile.weights()` (RNG-25's own anti-self-
intersection fix) says how much of the taper that side gets. A flat side at
weight 0 is a straight line at its own reference (`-th/2` inner, `+th/2`
outer); a domed or knife side at weight `d` is that same shape scaled by `d`
and re-centred so BOTH sides still meet at exactly the same point at the
band's edge -- see `_ellipse_half`/`_knife_edges` below for the arithmetic,
and `docs/research/shank-cross-section-profiles.md` for why a knife edge's
straight slopes and a court's ellipse are each the right shape for their name.
"""
from __future__ import annotations

from build123d import EllipticalCenterArc, Ellipse, Face, Line, Rectangle, Wire

from ringcad.ringspec.sections import SectionProfile


def _flat_line(x: float, half_w: float) -> list:
    return Line((x, -half_w, 0), (x, half_w, 0)).edges()


def _ellipse_half(th: float, half_w: float, d: float, *,
                   outer: bool) -> list:
    """A domed side's half-ellipse: `outer=True` bulges toward +x (the crown),
    `outer=False` toward -x (the valley), each carrying amplitude `d` of the
    taper and meeting the OTHER side's edge point exactly (see the module
    docstring)."""
    radius = th * d
    if outer:
        centre_x = th * (0.5 - d)
        start_angle = -90.0
    else:
        centre_x = th * (d - 0.5)
        start_angle = 90.0
    return EllipticalCenterArc(
        (centre_x, 0), radius, half_w, start_angle=start_angle, arc_size=180.0,
    ).edges()


def _knife_edges(th: float, half_w: float, d: float, apex_fraction: float) -> list:
    """The knife edge's outer boundary: flat crown (`|s| <= a`) then two
    straight slopes down to the edge point every other side also reaches."""
    a = min(apex_fraction, 1.0)
    x_edge = th * (0.5 - d)
    x_crown = th * 0.5
    if a >= 1.0:
        return _flat_line(x_crown, half_w)
    y_a = a * half_w
    points = [
        (x_edge, -half_w, 0), (x_crown, -y_a, 0),
        (x_crown, y_a, 0), (x_edge, half_w, 0),
    ]
    edges = []
    for p, q in zip(points, points[1:]):
        edges.extend(Line(p, q).edges())
    return edges


def _outer_edges(profile: SectionProfile, th: float, half_w: float,
                  d_o: float, apex_fraction: float) -> list:
    if d_o == 0.0:
        return _flat_line(th * 0.5, half_w)
    if profile.outer_profile == "knife_edge":
        return _knife_edges(th, half_w, d_o, apex_fraction)
    return _ellipse_half(th, half_w, d_o, outer=True)


def _inner_edges(profile: SectionProfile, th: float, half_w: float,
                  d_i: float) -> list:
    if d_i == 0.0:
        return _flat_line(-th * 0.5, half_w)
    return _ellipse_half(th, half_w, d_i, outer=False)


def section_face(profile: SectionProfile, th: float, w: float,
                  apex_fraction: float = 1.0):
    """The section's closed 2D face, centred on the plane origin exactly as
    the pre-RNG-25 `Ellipse(th/2, w/2)` was -- `_band_section` (CP2) positions
    it with the same `Plane(origin=..., x_dir=..., z_dir=...)` transform for
    every profile."""
    if profile.outer_profile == "domed" and profile.inner_profile == "domed":
        return Ellipse(th / 2, w / 2)

    d_o, d_i = profile.weights()
    if d_o == 0.0 and d_i == 0.0:
        # `flat` + `flat`: the only pairing whose two straight edges do NOT
        # meet at s=+-1 (outer stays at +th/2, inner at -th/2, a full-height
        # gap) -- a literal rectangle, closing sides included, rather than
        # the general open outer+inner assembly below.
        return Rectangle(th, w)
    half_w = w / 2
    outer = _outer_edges(profile, th, half_w, d_o, apex_fraction)
    inner = _inner_edges(profile, th, half_w, d_i)
    return Face(Wire(list(outer) + list(inner)))
