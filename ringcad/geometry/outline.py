"""StoneOutline — the centre stone's girdle, as a shape the modules can query
(RNG-23).

Before this, `c["stone_r"]` was a scalar and six sites assumed the girdle was a
circle: the seat torus, the claw ring, the bezel wall, the halo accent ring, and
the trilogy / overcrowding clearances. Adding a shape by branching on it in each
of those would scatter the same `if` six ways. Instead the shape answers
questions and the modules stay shape-blind:

  * **Curve-walkers** (seat / bezel / prong_setting / halo) place geometry AROUND
    the girdle -- they need `wire()`, `prong_angles()` and `frame_at()`.
  * **Width-consumers** (trilogy placement, overcrowding checks) need only one
    number, `half_width(axis)`. Handing them a curve would be a fake dependency.

Round is the degenerate case INSIDE this abstraction, never a branch beside it,
and `RoundOutline` deliberately reproduces the pre-RNG-23 numbers exactly so no
existing archetype's geometry moves.

Frame convention (local setting frame, before `placement()` maps it onto the
global +X head axis): local Y is band-tangential, i.e. along the finger, so an
oval set N-S by convention has its SEMI-MAJOR axis on local Y and its semi-minor
across the band on local X.
"""
from __future__ import annotations

import math
from typing import Protocol, runtime_checkable

from build123d import (
    CenterArc, Circle, Ellipse, Face, Line, Plane, Pos, Spline, Torus,
    Vector, Wire, extrude, sweep,
)

from ringcad.ringspec.cuts import (
    ArcSeg, LineSeg, ProngType, SplineSeg, profile_for,
)

TWO_PI = 2 * math.pi

# How far the bored seat's OUTER wall stands proud of the collar radius, so that
# anything sitting ON the girdle -- the claws, whose node sphere is centred there
# -- is embedded in the plate volumetrically rather than grazing its wall.
#
# Not a designed dimension; a construction margin, the same kind as
# `prong_setting.NODE_OVERLAP` and `halo.BEAD_SINK`. Measured: the claw's girdle
# sphere has radius 0.46 against a 0.45 collar, so it protruded 0.01mm through a
# flat extruded wall and OCCT resolved that graze as a zero-volume lamina -- 323
# faces, 183 non-manifold edges, a second mesh "body" of exactly 0.000mm3, off a
# B-rep that was a single valid solid (docs/adr/0007). A swept torus never showed
# it because its doubly-curved surface cuts the sphere in a clean circle; a flat
# extruded wall does not. Only the OUTER wall moves: the bore stays exactly the
# stone's negative, which is the whole point of docs/adr/0008.
GIRDLE_EMBED = 0.06

# The tips of an elongated stone are the ends of the major axis: local +Y / -Y.
_TIP_ANGLE = math.pi / 2


def _check_axis(axis: str) -> None:
    if axis not in ("x", "y"):
        raise ValueError(f"axis must be 'x' or 'y', got {axis!r}")


@runtime_checkable
class StoneOutline(Protocol):
    """What every module is allowed to know about the centre stone's girdle."""

    def wire(self) -> Wire:
        """The closed girdle path, for sweeping a seat or bezel along."""

    def prong_angles(self, n: int) -> list[float]:
        """Where N prongs sit, in radians of the local frame.

        Retained as the angle-only view of `placements`; CP3's
        `prong_setting` reads `placements` so it can honour the prong TYPE.
        """

    def placements(self, n: int) -> list[tuple[float, "ProngType"]]:
        """Where N prongs sit AND what kind each one is.

        The type is geometric, not stylistic: `V` is the prong that wraps a
        vertex -- an emerald's cut corner, a pear's point, a marquise's two
        points. That makes it reusable for every cornered or pointed cut we
        add later rather than being a per-cut special case.
        """

    def seat_solid(self, minor_r: float):
        """The seat collar as a finished solid, centred on z = 0.

        The OUTLINE builds it, not `seat()`, because how a seat is made depends
        on the girdle: a smooth curve can have a collar swept along it, while a
        girdle with vertices cannot be swept at ANY section radius and has its
        seat bored out of a plate instead (docs/adr/0008). `seat()` stays
        shape-blind either way.
        """

    def frame_at(self, theta: float) -> tuple[Vector, Vector]:
        """(point on the girdle, outward unit normal) at angle `theta`."""

    def half_width(self, axis: str) -> float:
        """Reach from centre to girdle along 'x' (across band) or 'y' (along)."""

    def min_curvature_radius(self) -> float:
        """Radius of the tightest bend anywhere on the girdle.

        The casting floors are hardest to hold where the girdle bends most
        sharply, so this is what a min-wall / min-tip check must be measured
        against for a non-round stone.
        """

    def tube(self, minor_r: float):
        """The girdle tube of section radius `minor_r` -- the seat collar.

        Built by the outline rather than by `seat()` so the round case can keep
        its original `Torus` call verbatim. Sweeping a circle along a circular
        path would be mathematically equivalent but not numerically identical,
        and the parity / golden suites pin today's round output.
        """

    def expanded(self, distance: float) -> "StoneOutline":
        """The same shape grown outward by `distance` -- the curve a halo ring or
        a bezel wall sits on."""

    def angles_by_arc(self, n: int, offset: float = 0.0) -> list[float]:
        """`n` angles spaced equally by ARC LENGTH, not by angle.

        Equal angles crowd features toward the tips of an elongated shape, where
        the curve travels fastest per radian, so a halo that looks even in polar
        coordinates is visibly bunched in metal. `offset` shifts the whole set by
        that fraction of one step (0.5 = the gap midpoints, for shared prongs).
        """


class RoundOutline:
    """A circular girdle: the pre-RNG-23 behaviour, unchanged."""

    def __init__(self, radius: float) -> None:
        self.radius = float(radius)

    def wire(self) -> Wire:
        return Circle(self.radius).wire()

    def prong_angles(self, n: int) -> list[float]:
        # Even spacing -- identical to prong_setting's original `i * 360/n`.
        return [k * TWO_PI / n for k in range(n)]

    def frame_at(self, theta: float) -> tuple[Vector, Vector]:
        direction = Vector(math.cos(theta), math.sin(theta), 0)
        return direction * self.radius, direction

    def half_width(self, axis: str) -> float:
        _check_axis(axis)
        return self.radius

    def min_curvature_radius(self) -> float:
        return self.radius

    def placements(self, n: int) -> list[tuple[float, ProngType]]:
        return [(t, ProngType.ROUND) for t in self.prong_angles(n)]

    def tube(self, minor_r: float):
        # The pre-RNG-23 seat call, unchanged: `Torus(stone_r, collar_tr)`.
        return Torus(self.radius, minor_r)

    def seat_solid(self, minor_r: float):
        return self.tube(minor_r)

    def expanded(self, distance: float) -> "RoundOutline":
        return RoundOutline(self.radius + distance)

    def angles_by_arc(self, n: int, offset: float = 0.0) -> list[float]:
        # On a circle equal arc IS equal angle, so return the analytic values
        # rather than a numerical inversion -- this keeps the existing halo ring
        # bit-identical.
        return [TWO_PI * (k + offset) / n for k in range(n)]


class OvalOutline:
    """An elliptical girdle, semi-major along local Y (set N-S by convention)."""

    def __init__(self, semi_minor: float, semi_major: float) -> None:
        self.semi_minor = float(semi_minor)  # across the band (local X)
        self.semi_major = float(semi_major)  # along the band (local Y)

    def wire(self) -> Wire:
        # build123d's Ellipse takes (x_radius, y_radius) -- minor on X, major on Y.
        return Ellipse(self.semi_minor, self.semi_major).wire()

    def prong_angles(self, n: int) -> list[float]:
        """Place prongs so the TIPS fall exactly midway between adjacent claws.

        The apex of the major axis is both the highest-curvature point (worst
        place to hold the min tip diameter) and the classic snag point on a real
        oval, so no claw belongs there. Offsetting by half a step from the tip
        gives the conventional 10-2-4-8 layout at n=4 and leaves the tips a clear
        30 degrees from any claw at n=6 -- one formula, no per-count casing.
        """
        step = TWO_PI / n
        return [_TIP_ANGLE + (k + 0.5) * step for k in range(n)]

    def frame_at(self, theta: float) -> tuple[Vector, Vector]:
        p, q = self.semi_minor, self.semi_major
        point = Vector(p * math.cos(theta), q * math.sin(theta), 0)
        # Outward normal of an ellipse is NOT radial (except on the axes): it is
        # the gradient of x^2/p^2 + y^2/q^2, i.e. (q cos t, p sin t) normalised.
        normal = Vector(q * math.cos(theta), p * math.sin(theta), 0).normalized()
        return point, normal

    def half_width(self, axis: str) -> float:
        _check_axis(axis)
        return self.semi_minor if axis == "x" else self.semi_major

    def min_curvature_radius(self) -> float:
        # Tightest bend is at the end of the major axis: p^2 / q.
        return self.semi_minor ** 2 / self.semi_major

    def expanded(self, distance: float) -> "OvalOutline":
        """Grow both semi-axes by `distance`.

        Deliberately NOT the exact parallel curve of an ellipse, which is a
        higher-degree curve and not an ellipse at all. Growing both axes keeps the
        result a clean ellipse the kernel can sweep, and the error against the
        true offset is largest at the tips and small at the scale of a halo gap.
        A jeweller lays out a halo the same way.
        """
        return OvalOutline(self.semi_minor + distance, self.semi_major + distance)

    def _arc_table(self, samples: int = 4096) -> tuple[list[float], float]:
        """Cumulative arc length at `samples` equally-spaced parameter values.

        Integrated here rather than read off the kernel wire: OCCT reports this
        ellipse's length ~0.13% high (see tests/test_stone_outline.py), and the
        accent spacing should not inherit that.
        """
        p, q = self.semi_minor, self.semi_major
        cumulative = [0.0]
        prev_x, prev_y = p, 0.0
        for i in range(1, samples + 1):
            t = TWO_PI * i / samples
            x, y = p * math.cos(t), q * math.sin(t)
            cumulative.append(
                cumulative[-1] + math.hypot(x - prev_x, y - prev_y)
            )
            prev_x, prev_y = x, y
        return cumulative, cumulative[-1]

    def angles_by_arc(self, n: int, offset: float = 0.0) -> list[float]:
        cumulative, total = self._arc_table()
        samples = len(cumulative) - 1
        angles = []
        for k in range(n):
            target = total * (k + offset) / n
            # Invert the cumulative table by linear interpolation.
            lo, hi = 0, samples
            while lo < hi:
                mid = (lo + hi) // 2
                if cumulative[mid] < target:
                    lo = mid + 1
                else:
                    hi = mid
            if lo == 0:
                angles.append(0.0)
                continue
            span = cumulative[lo] - cumulative[lo - 1]
            frac = (target - cumulative[lo - 1]) / span if span else 0.0
            angles.append(TWO_PI * (lo - 1 + frac) / samples)
        return angles

    def tube(self, minor_r: float):
        """Sweep the collar section along the ellipse.

        The section plane's normal must lie along the path tangent at the start
        point (semi_minor, 0), which is +Y -- a section oriented radially instead
        produces a null solid rather than an error, so this orientation is
        load-bearing.
        """
        section = Plane(
            origin=(self.semi_minor, 0, 0), x_dir=(1, 0, 0), z_dir=(0, 1, 0)
        ) * Circle(minor_r)
        return sweep(section, self.wire(), is_frenet=True)

    def placements(self, n: int) -> list[tuple[float, ProngType]]:
        return [(t, ProngType.CLAW) for t in self.prong_angles(n)]

    def seat_solid(self, minor_r: float):
        return self.tube(minor_r)


class ProfileOutline:
    """One kernel adapter over ANY `CutProfile` (RNG-33).

    RNG-23 promised that a new cut would be a new outline class rather than an
    edit to six modules. CP1 went one better: every shape-specific fact -- the
    girdle construction, the prong rule, the proportions -- lives in the
    profile, so the kernel side is written once and a new cut needs no geometry
    code at all.

    Round and oval deliberately do NOT come through here. Their construction is
    pinned bit-identical by the parity and golden suites, and routing them
    through a generic adapter would move them for no gain.
    """

    def __init__(self, profile, half_short: float, ratio: float) -> None:
        self.profile = profile
        self.half_short = float(half_short)
        self.ratio = float(ratio)

    # --- the girdle path --------------------------------------------------

    def wire(self) -> Wire:
        """Build the girdle from the profile's EXACT segments.

        Not from a sampled spline: an emerald's corners and a marquise's points
        are the identity of those cuts, and sampling them away still yields a
        closed, faceable, watertight wire that merely looks wrong -- the kind of
        failure that passes every structural assertion.
        """
        edges = []
        for seg in self.profile.segments(self.half_short, self.ratio):
            if isinstance(seg, LineSeg):
                shape = Line((seg.a[0], seg.a[1], 0), (seg.b[0], seg.b[1], 0))
            elif isinstance(seg, ArcSeg):
                shape = Pos(seg.centre[0], seg.centre[1], 0) * CenterArc(
                    (0, 0, 0), seg.radius,
                    math.degrees(seg.start),
                    math.degrees(seg.end - seg.start))
            elif isinstance(seg, SplineSeg):
                shape = Spline(*[(x, y, 0) for x, y in seg.points],
                               periodic=True)
            else:                                     # pragma: no cover
                raise TypeError(f"unknown girdle segment {seg!r}")
            # Every builder here returns a Curve (a compound), never a bare
            # Edge, so collect edges uniformly rather than special-casing the
            # single-segment cut.
            edges.extend(shape.edges())
        return Wire(edges)

    def frame_at(self, theta: float) -> tuple[Vector, Vector]:
        """(point, outward unit normal) at POLAR angle `theta`.

        The normal is the mean of the two adjacent sampled tangent normals, so
        at a vertex it is the angle BISECTOR -- which is exactly the direction a
        V-prong has to come from to wrap that corner.
        """
        p = self.profile
        eps = 1e-3
        point = p.point_at(theta, self.half_short, self.ratio)
        before = p.point_at(theta - eps, self.half_short, self.ratio)
        after = p.point_at(theta + eps, self.half_short, self.ratio)
        tangent = Vector(after[0] - before[0], after[1] - before[1], 0)
        normal = Vector(tangent.Y, -tangent.X, 0)
        if normal.length < 1e-12:                     # pragma: no cover
            normal = Vector(point[0], point[1], 0)
        normal = normal.normalized()
        if normal.dot(Vector(point[0], point[1], 0)) < 0:
            normal = normal * -1                      # keep it pointing out
        return Vector(point[0], point[1], 0), normal

    # --- width-consumers --------------------------------------------------

    def half_width(self, axis: str) -> float:
        return self.profile.half_width(self.half_short, self.ratio, axis)

    def min_curvature_radius(self) -> float:
        return self.profile.min_curvature_radius(self.half_short, self.ratio)

    # --- prongs -----------------------------------------------------------

    def prong_angles(self, n: int) -> list[float]:
        return [t for t, _ in self.placements(n)]

    def placements(self, n: int) -> list[tuple[float, ProngType]]:
        return self.profile.prong_layout(n)

    # --- derived curves ---------------------------------------------------

    def expanded(self, distance: float) -> "ProfileOutline":
        """Grow both semi-axes by `distance`.

        Deliberately NOT the true parallel curve, exactly as `OvalOutline`
        already chooses: the offset of any of these outlines is a higher-degree
        curve that the kernel cannot sweep or face as cleanly, the error is
        largest at the tips and small at the scale of a halo gap, and a jeweller
        lays a halo out this way. Keeping the SAME approximation as oval also
        means the halo plate and its bore stay the same kind of curve.
        """
        p = self.half_short + distance
        q = self.half_short * self.ratio + distance
        return ProfileOutline(self.profile, p, q / p if p else 1.0)

    def angles_by_arc(self, n: int, offset: float = 0.0) -> list[float]:
        return self.profile.angles_by_arc(
            n, self.half_short, self.ratio, offset)

    # --- the seat ---------------------------------------------------------

    def tube(self, minor_r: float):
        """Kept for interface compatibility; the seat is BORED, not swept."""
        return self.seat_solid(minor_r)

    def seat_solid(self, minor_r: float):
        """A bearing plate with the stone's own negative cut out of it.

        docs/adr/0008, third customer. A collar tube swept along this girdle is
        not merely hard, it is impossible: a vertex has no radius, so the sweep
        self-intersects at ANY section radius. Cutting instead makes the
        remaining metal whatever the bore leaves, which is what a metal-only
        semi-mount should show anyway.

        The bore is cut OVERSIZE in height so it breaks through both faces. A
        bore landing flush with a face leaves a lid, and that seat becomes a
        sealed internal cavity that still reports watertight, single-solid and
        all-floors-met -- the trap ADR-0008 names and ADR-0005 was written for.
        """
        if self.half_short <= minor_r + GIRDLE_EMBED:
            # Below this the inner bore inverts. Pear and marquise raise out of
            # OCCT, but cushion and emerald quietly return a plausible SOLID
            # with no opening at all -- wrong metal, no error, and every
            # structural assertion still green. That is the ADR-0008 trap with
            # the sealed void replaced by a mirrored one, so it is refused here
            # rather than left to be noticed. The casting gate already rejects
            # stones this small on the prong-tip floor; this guards the module
            # against being called directly.
            raise ValueError(
                f"stone half-width {self.half_short:.3f}mm is not larger than "
                f"the {minor_r:.3f}mm seat collar: no seat can be bored"
            )
        h = 2 * minor_r
        body = extrude(
            Face(self.expanded(minor_r + GIRDLE_EMBED).wire()), amount=h)
        bore = extrude(Face(self.expanded(-minor_r).wire()), amount=h + 1.0)
        return Pos(0, 0, -h / 2) * (body - Pos(0, 0, -0.5) * bore)


def outline_for(shape: str, half_width: float, length_ratio: float) -> StoneOutline:
    """Build the outline for a RingSpec stone group.

    `half_width` is stone_diameter/2 (the SHORT axis); `length_ratio` is
    long/short, so 1.0 is round and the round path is taken whenever the stone is
    effectively circular -- keeping existing geometry bit-identical.

    Round and oval keep their own classes; every other cut goes through the
    shared `ProfileOutline`, which needs no per-cut kernel code.
    """
    if length_ratio <= 1.0 and shape in ("round", "oval"):
        return RoundOutline(half_width)
    if shape == "round":
        return RoundOutline(half_width)
    if shape == "oval":
        return OvalOutline(half_width, half_width * length_ratio)
    return ProfileOutline(profile_for(shape), half_width, length_ratio)
