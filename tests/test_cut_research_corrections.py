"""Two cited corrections to shipped cut geometry (RNG-33, research 2026-08-24).

The frozen spec listed both of these under "Invented -- no trade or standards
figure found". A second research pass found figures for both. See
`docs/research/cut-outline-geometry-cushion-emerald.md` and
`docs/research/cut-outline-geometry-pear-marquise.md`.

**Pear wings were straight, and straight is the named defect.** `PearProfile`
built the wing as the tangent LINE from the head circle to the point, and its
docstring claimed that construction "produces none of" the trade's named
defects. It produces one of them: trade sources define the defects symmetrically
around a curved ideal -- "bulged wings" (too convex) and "flat wings" (too
straight) -- so a correct wing is a gently convex curve between belly and point.
Four independent sources converge, GIA's own 4Cs guide among them.

**Emerald corners were 15% of the width; the figure is 13.5-14.5%.** Two
independent primary sources define the same quantity under the same name: US
Patent 10,448,713 B1 ("a variable corner ratio CR, i.e., the ratio of the corner
width to the width W") and the American Gem Society's "Emerald Cut Geometry"
reference, whose labeled diagram settles that CR spans ONE corner rather than
the pair -- which is what makes it comparable to our `corner_fraction` at all.

What did NOT change, because the sources still do not say: the pear's belly
position, the marquise tip angle, the tip radius, and the V-prong's reach. Those
remain ours, and the notes record that the search was thorough rather than
absent.
"""
from __future__ import annotations

import math

import pytest

from ringcad.ringspec.cuts import profile_for

PEAR_RATIOS = (1.15, 1.6, 2.1)


def _turns(pts):
    """Turn angle at each polyline joint, with the point it belongs to."""
    out = []
    n = len(pts)
    for i in range(n):
        a, b, c = pts[i - 1], pts[i], pts[(i + 1) % n]
        v1 = (b[0] - a[0], b[1] - a[1])
        v2 = (c[0] - b[0], c[1] - b[1])
        out.append((abs(math.atan2(v1[0] * v2[1] - v1[1] * v2[0],
                                   v1[0] * v2[0] + v1[1] * v2[1])), b))
    return out


def _wing_joints(pts, half, ratio):
    """Joints on the RIGHT wing, with each one's local radius of curvature.

    Identified by GEOMETRY rather than by asking the profile which segment is
    which, so the test cannot be satisfied by relabelling the construction:
    above the belly, right of the axis, clear of the point, and not part of the
    head -- the head being the run whose radius is the head radius. Selecting
    on position alone swept the head's upper shoulders in and made the radius
    test report the head's own 3.25mm as the tightest "wing" curvature.
    """
    step = math.dist(pts[0], pts[1])
    belly_y = max(pts, key=lambda q: q[0])[1]
    tip_y = half * ratio
    out = []
    for turn, b in _turns(pts):
        if not (b[0] > 1e-9 and belly_y + 1e-6 < b[1] < tip_y - 0.02 * tip_y):
            continue
        radius = math.inf if turn <= 0 else step / turn
        if abs(radius - half) <= 0.1 * half:      # this joint is the head
            continue
        out.append((turn, b, radius))
    # Drop the joints at each END of the run. The polyline samples the head and
    # the wing as separate arcs, so the joint where they meet spans one step of
    # each and reports a curvature that is neither -- an artefact of sampling
    # two curves, not a feature of the shape. Measured: it reads 4.56mm on a
    # wing whose every other joint reads 7.66mm.
    return out[1:-1] if len(out) > 2 else out


# --- pear: the wings bow outward -------------------------------------------

@pytest.mark.parametrize("ratio", PEAR_RATIOS)
def test_pear_wings_curve_along_their_whole_length(ratio):
    """The correction itself, stated as the property that actually separates
    the two shapes: a STRAIGHT wing has zero curvature everywhere along it, a
    gently rounded one has curvature everywhere.

    An earlier version of this test measured the wing's bulge against a chord
    anchored at the BELLY -- and passed against the straight wings it was
    written to reject, because that chord spans part of the head arc, whose
    convexity it was really measuring (docs/adr/0010). Curvature along the wing
    is the thing itself, not a proxy for it.
    """
    joints = _wing_joints(profile_for("pear")._polyline(3.25, ratio),
                          3.25, ratio)
    assert len(joints) > 8, "no wing run found"
    flat = [t for t, _, _ in joints if t < 1e-6]
    assert not flat, (
        f"pear wing at ratio {ratio} has {len(flat)} of {len(joints)} joints "
        "with no curvature at all -- that is a straight wing"
    )


@pytest.mark.parametrize("ratio", PEAR_RATIOS)
def test_pear_wing_curves_gently_not_bulbously(ratio):
    """"Bulged wings" is a defect too, so the correction has to land between
    the two named failures rather than swap one for the other. The wing's
    radius of curvature must stay well ABOVE the head's -- a wing curving as
    tightly as the head would read as a second belly."""
    half = 3.25
    joints = _wing_joints(profile_for("pear")._polyline(half, ratio),
                          half, ratio)
    radii = [r for _, _, r in joints if math.isfinite(r)]
    assert radii, "no curving wing run found"
    assert min(radii) > 1.5 * half, (
        f"tightest wing radius {min(radii):.2f}mm against a {half:.2f}mm head "
        f"at ratio {ratio} -- that is a bulge, not a wing"
    )


@pytest.mark.parametrize("ratio", PEAR_RATIOS)
def test_pear_shoulder_has_no_kink(ratio):
    """Where the head meets the wing the curve must stay smooth.

    A convex wing that simply replaced the straight one, keeping the same
    junction, would leave a corner at the shoulder -- trading the "flat wings"
    defect for a "high shoulders" one. Tangent continuity is what rules that
    out, and it is why the junction had to MOVE rather than the wing merely
    being bent.
    """
    pts = profile_for("pear")._polyline(3.25, ratio)
    tip_y = 3.25 * ratio
    off_tip = [t for t, b in _turns(pts) if abs(b[1] - tip_y) > 0.05 * tip_y]
    assert max(off_tip) < 0.05, (
        f"kink of {math.degrees(max(off_tip)):.1f} degrees away from the point"
    )


@pytest.mark.parametrize("ratio", PEAR_RATIOS)
def test_pear_belly_stays_where_it_was(ratio):
    """The belly position is still OURS -- no published figure was found for it
    in either research pass -- so the wing correction must not quietly move it.
    It sits at 1/(2*ratio) of the length from the round end."""
    half = 3.25
    pts = profile_for("pear")._polyline(half, ratio)
    widest = max(pts, key=lambda q: q[0])
    length = 2 * half * ratio
    from_round_end = widest[1] - (-half * ratio)
    assert from_round_end / length == pytest.approx(1 / (2 * ratio), abs=0.01)
    assert widest[0] == pytest.approx(half, rel=1e-3), "half-width moved"


# --- emerald: the corner ratio is published --------------------------------

def test_emerald_corner_ratio_matches_the_published_band():
    """US10448713B1 gives CR = 13.5-14.5% of W, preferred 14.0%; AGS's
    "Emerald Cut Geometry" diagram confirms CR spans one corner. We were at
    15%, just outside it."""
    p = profile_for("emerald")
    assert 0.135 <= p.corner_fraction <= 0.145
    assert p.corner_fraction == pytest.approx(0.14)


@pytest.mark.parametrize("ratio", [1.05, 1.4, 1.75])
def test_emerald_corner_measures_the_published_fraction_of_the_width(ratio):
    """Asserted on the built OUTLINE, not on the constant, because the
    constant is only right if it means what the sources mean: the truncation
    of ONE corner, measured along the width."""
    p = profile_for("emerald")
    half = 3.25
    vs = p._vertices(half, ratio)
    top = sorted(vs, key=lambda v: -v[1])[:2]      # the two vertices of the top edge
    flat = abs(top[0][0] - top[1][0])
    width = 2 * half
    assert (width - flat) / 2 / width == pytest.approx(0.14, abs=0.005)
