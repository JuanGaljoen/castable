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

from build123d import Circle, Ellipse, Plane, Torus, Vector, Wire, sweep

TWO_PI = 2 * math.pi

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
        """Where N prongs sit, in radians of the local frame."""

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

    def tube(self, minor_r: float):
        # The pre-RNG-23 seat call, unchanged: `Torus(stone_r, collar_tr)`.
        return Torus(self.radius, minor_r)

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


def outline_for(shape: str, half_width: float, length_ratio: float) -> StoneOutline:
    """Build the outline for a RingSpec stone group.

    `half_width` is stone_diameter/2 (the SHORT axis); `length_ratio` is
    long/short, so 1.0 is round and the round path is taken whenever the stone is
    effectively circular -- keeping existing geometry bit-identical.
    """
    if shape == "oval" and length_ratio > 1.0:
        return OvalOutline(half_width, half_width * length_ratio)
    return RoundOutline(half_width)
