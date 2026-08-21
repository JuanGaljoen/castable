"""CutProfile — everything a centre-stone cut knows about itself (RNG-33).

**Kernel-free by design.** This module imports no `build123d`, so both sides can
read the same numbers:

  * `ringcad.ringspec.castability` ASKS a profile instead of re-deriving the
    math (it used to recompute `semi_minor / ratio` inline while
    `outline.min_curvature_radius()` had no production caller at all -- exactly
    the drift docs/adr/0002 warns about);
  * `ringcad.geometry.outline` WRAPS a profile and adds only what needs the
    kernel: `wire()`, `frame_at()`, the seat solids.

Spec layer owns the shape FACTS; geometry layer owns the kernel CONSTRUCTION.

Frame convention, inherited from RNG-23: local **X is across the band**, local
**Y is along the finger**, so an elongated stone is set N-S with its long axis on
Y. `half_short` is `stone_diameter / 2`; the long semi-axis is
`half_short * length_ratio`.

Two parametrisations coexist, deliberately. `RoundProfile` and `OvalProfile` keep
RNG-23's ECCENTRIC angle (`p cos t, q sin t`) so their geometry is untouched;
every new cut uses the POLAR angle, which is what a ray-cast against a polygon or
a piecewise arc naturally gives. That is safe because theta never crosses an
outline boundary -- one outline's `prong_layout` and its `point_at` always speak
the same convention. Per-cut parametrisation is what "the outline owns it" means.

Everything except the two analytic cases derives numerically from one polyline
the subclass builds. A new cut is therefore a `_polyline` plus a prong rule --
perimeter, curvature, arc spacing and polar lookup all come free.
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from enum import Enum

TWO_PI = 2 * math.pi

# The tip of an elongated stone is the end of the long axis: local +Y.
_TIP_ANGLE = math.pi / 2

# Polyline resolution. High enough that the numeric perimeter and curvature are
# well inside any casting tolerance, cheap enough to call per build.
_SAMPLES = 2048

# Turn angle (radians) above which a polyline joint is a VERTEX rather than a
# sampled curve. At _SAMPLES resolution a smooth curve turns ~0.003 rad per
# joint, so this is three orders of magnitude clear of the noise floor.
_VERTEX_TURN = 0.15


@dataclass(frozen=True)
class LineSeg:
    """A straight girdle run, from `a` to `b`."""

    a: tuple[float, float]
    b: tuple[float, float]


@dataclass(frozen=True)
class ArcSeg:
    """A circular girdle run, swept CCW from `start` to `end` (radians)."""

    centre: tuple[float, float]
    radius: float
    start: float
    end: float


@dataclass(frozen=True)
class SplineSeg:
    """A smooth girdle run through `points`, for cuts with no exact primitive."""

    points: tuple[tuple[float, float], ...]


class ProngType(str, Enum):
    """What kind of prong sits at a placement.

    The distinction is geometric, not stylistic: **V is the prong that wraps a
    VERTEX** -- an emerald's cut corner, a pear's point, a marquise's two
    points. A rounded corner or a smooth girdle takes a claw instead. Tying the
    type to the geometry rather than to per-cut taste is what makes it reusable
    for princess, heart, trillion and shield later.
    """

    ROUND = "round"
    CLAW = "claw"
    V = "V"


def _check_axis(axis: str) -> None:
    if axis not in ("x", "y"):
        raise ValueError(f"axis must be 'x' or 'y', got {axis!r}")


def _polar(x: float, y: float) -> float:
    return math.atan2(y, x) % TWO_PI


@dataclass(frozen=True)
class CutProfile:
    """One cut's proportions, outline construction and prong rule.

    Immutable and sized-on-demand: the profile is the CUT, not a particular
    stone, so every method that needs a size takes `half_short` and `ratio`.
    """

    name: str
    default_ratio: float
    min_ratio: float
    max_ratio: float
    has_vertices: bool = False
    tip_radius: float = 0.0

    # --- construction, overridden per cut ---------------------------------

    def _polyline(self, half_short: float, ratio: float,
                  samples: int = _SAMPLES) -> list[tuple[float, float]]:
        raise NotImplementedError

    def prong_layout(self, n: int) -> list[tuple[float, ProngType]]:
        raise NotImplementedError

    def segments(self, half_short: float, ratio: float) -> list:
        """The girdle as EXACT pieces, for the kernel to build a wire from.

        Defaults to one spline through a coarse sampling, which is right for a
        smooth cut and wrong for a cornered one: sampling a vertex into a spline
        rounds it off, and the result still closes, still faces, still reads
        watertight and still looks roughly right. Cuts with vertices override
        this and say exactly where their edges are.
        """
        pts = self._polyline(half_short, ratio, samples=192)
        return [SplineSeg(tuple(pts))]

    # --- shared numeric core ----------------------------------------------

    def half_width(self, half_short: float, ratio: float, axis: str) -> float:
        """Reach from centre to girdle across the band ('x') or along it ('y').

        Every cut here is inscribed in its bounding box, so this is exact
        without touching the polyline.
        """
        _check_axis(axis)
        return half_short if axis == "x" else half_short * ratio

    def perimeter(self, half_short: float, ratio: float) -> float:
        pts = self._polyline(half_short, ratio)
        return sum(
            math.dist(pts[i], pts[(i + 1) % len(pts)]) for i in range(len(pts))
        )

    def min_curvature_radius(self, half_short: float, ratio: float) -> float:
        """Tightest bend on the SMOOTH parts of the girdle.

        Vertices are excluded rather than reported as radius zero. A vertex is
        not a tight curve -- it cannot be swept along by a collar tube at any
        radius, which is why those seats are bored instead (docs/adr/0008). A
        gate that read a vertex as "infinitely tight curvature" would reject
        every cornered cut outright, which is the wrong answer to the wrong
        question. `has_vertices` is how a caller asks that separately.
        """
        pts = self._polyline(half_short, ratio)
        n = len(pts)
        best = math.inf
        for i in range(n):
            a, b, c = pts[i - 1], pts[i], pts[(i + 1) % n]
            v1 = (b[0] - a[0], b[1] - a[1])
            v2 = (c[0] - b[0], c[1] - b[1])
            turn = abs(math.atan2(
                v1[0] * v2[1] - v1[1] * v2[0], v1[0] * v2[0] + v1[1] * v2[1]))
            if turn > _VERTEX_TURN or turn < 1e-12:
                continue                      # a vertex, or a straight run
            # Circumradius of the three sampled points.
            la, lb, lc = math.dist(b, c), math.dist(a, c), math.dist(a, b)
            area2 = abs((b[0] - a[0]) * (c[1] - a[1])
                        - (c[0] - a[0]) * (b[1] - a[1]))
            if area2 <= 0:
                continue
            best = min(best, la * lb * lc / (2 * area2))
        return best

    def point_at(self, theta: float, half_short: float,
                 ratio: float) -> tuple[float, float]:
        """The girdle point at polar angle `theta`.

        Every outline here is star-shaped about the centre, so polar angle
        increases monotonically along the polyline and a ray cast is a lookup.
        """
        pts = self._polyline(half_short, ratio)
        t = theta % TWO_PI
        n = len(pts)
        for i in range(n):
            a, b = pts[i], pts[(i + 1) % n]
            pa, pb = _polar(*a), _polar(*b)
            if pb < pa:                        # the wrap-around segment
                pb += TWO_PI
            tt = t if t >= pa else t + TWO_PI
            if pa <= tt <= pb:
                span = pb - pa
                f = (tt - pa) / span if span else 0.0
                return (a[0] + f * (b[0] - a[0]), a[1] + f * (b[1] - a[1]))
        return pts[0]

    def angles_by_arc(self, n: int, half_short: float, ratio: float,
                      offset: float = 0.0) -> list[float]:
        """`n` polar angles spaced equally by ARC LENGTH, not by angle.

        Equal angles crowd features toward the ends of an elongated shape, where
        the curve travels fastest per radian (RNG-23). `offset` shifts the whole
        set by that fraction of one step.
        """
        pts = self._polyline(half_short, ratio)
        cum = [0.0]
        for i in range(len(pts)):
            cum.append(cum[-1] + math.dist(pts[i], pts[(i + 1) % len(pts)]))
        total = cum[-1]
        out = []
        for k in range(n):
            target = total * ((k + offset) / n % 1.0)
            lo, hi = 0, len(cum) - 1
            while lo < hi:
                mid = (lo + hi) // 2
                if cum[mid] < target:
                    lo = mid + 1
                else:
                    hi = mid
            idx = max(lo - 1, 0)
            a, b = pts[idx % len(pts)], pts[(idx + 1) % len(pts)]
            span = cum[idx + 1] - cum[idx]
            f = (target - cum[idx]) / span if span else 0.0
            out.append(_polar(a[0] + f * (b[0] - a[0]),
                              a[1] + f * (b[1] - a[1])))
        return out

    def _arc_table(self, half_short: float, ratio: float):
        pts = self._polyline(half_short, ratio)
        cum = [0.0]
        for i in range(len(pts)):
            cum.append(cum[-1] + math.dist(pts[i], pts[(i + 1) % len(pts)]))
        return pts, cum, cum[-1]

    def _at_arc(self, s: float, pts, cum) -> float:
        """Polar angle at cumulative arc length `s` (wrapping)."""
        total = cum[-1]
        s %= total
        lo, hi = 0, len(cum) - 1
        while lo < hi:
            mid = (lo + hi) // 2
            if cum[mid] < s:
                lo = mid + 1
            else:
                hi = mid
        idx = max(lo - 1, 0)
        a, b = pts[idx % len(pts)], pts[(idx + 1) % len(pts)]
        span = cum[idx + 1] - cum[idx]
        f = (s - cum[idx]) / span if span else 0.0
        return _polar(a[0] + f * (b[0] - a[0]), a[1] + f * (b[1] - a[1]))

    def _arc_of(self, theta: float, pts, cum) -> float:
        """Cumulative arc length at polar angle `theta`."""
        t = theta % TWO_PI
        for i in range(len(pts)):
            pa, pb = _polar(*pts[i]), _polar(*pts[(i + 1) % len(pts)])
            if pb < pa:
                pb += TWO_PI
            tt = t if t >= pa else t + TWO_PI
            if pa <= tt <= pb:
                span = pb - pa
                f = (tt - pa) / span if span else 0.0
                return cum[i] + f * (cum[i + 1] - cum[i])
        return 0.0

    def _place_between(self, fixed: list[tuple[float, ProngType]], n: int,
                       half_short: float, ratio: float,
                       kind: ProngType) -> list[tuple[float, ProngType]]:
        """Fixed prongs first, then share the rest evenly BY ARC in each gap.

        The angular positions of a pear's or marquise's side prongs are not
        published anywhere -- the trade describes them only as "two on each side
        curve". Rather than invent angles, distribute them by arc length (the
        repo's existing convention since RNG-23) within the gaps the fixed
        prongs leave. On a shape symmetric about the long axis this is symmetric
        BY CONSTRUCTION, and it lands the pear's 4th prong exactly on the round
        end and the marquise's side prongs exactly on the widest point.
        """
        want = n - len(fixed)
        if want <= 0:
            return list(fixed)[:n]
        pts, cum, total = self._arc_table(half_short, ratio)
        anchors = sorted(self._arc_of(t, pts, cum) for t, _ in fixed)
        gaps = [
            (anchors[i], (anchors[(i + 1) % len(anchors)]
                          - anchors[i]) % total or total)
            for i in range(len(anchors))
        ]
        # Longest gaps take the surplus when `want` does not divide evenly.
        per = [want // len(gaps)] * len(gaps)
        for i in sorted(range(len(gaps)), key=lambda i: -gaps[i][1])[
                :want % len(gaps)]:
            per[i] += 1
        out = list(fixed)
        for (start, span), count in zip(gaps, per):
            for k in range(1, count + 1):
                out.append((self._at_arc(start + span * k / (count + 1),
                                         pts, cum), kind))
        return out


# --- the cuts ---------------------------------------------------------------

@dataclass(frozen=True)
class RoundProfile(CutProfile):
    """A circle. Every value analytic, so nothing about round can drift."""

    def _polyline(self, half_short, ratio, samples=_SAMPLES):
        return [(half_short * math.cos(TWO_PI * i / samples),
                 half_short * math.sin(TWO_PI * i / samples))
                for i in range(samples)]

    def perimeter(self, half_short, ratio):
        return TWO_PI * half_short

    def min_curvature_radius(self, half_short, ratio):
        return half_short

    def prong_layout(self, n):
        # Identical to prong_setting's original `i * 360/n`.
        return [(k * TWO_PI / n, ProngType.ROUND) for k in range(n)]


@dataclass(frozen=True)
class OvalProfile(CutProfile):
    """An ellipse, semi-major along local Y. Parametrised by ECCENTRIC angle,
    exactly as RNG-23 left it, so no existing oval geometry moves."""

    def _polyline(self, half_short, ratio, samples=_SAMPLES):
        p, q = half_short, half_short * ratio
        return [(p * math.cos(TWO_PI * i / samples),
                 q * math.sin(TWO_PI * i / samples)) for i in range(samples)]

    def min_curvature_radius(self, half_short, ratio):
        # Tightest bend at the apex of the major axis: p^2 / q.
        return half_short / ratio if ratio else half_short

    def prong_layout(self, n):
        """Tips fall midway between adjacent claws -- the 10-2-4-8 layout at
        n=4 (RNG-23). The apex is the worst place to hold a min tip AND the
        classic snag point, so no claw belongs there."""
        step = TWO_PI / n
        return [(_TIP_ANGLE + (k + 0.5) * step, ProngType.CLAW)
                for k in range(n)]


@dataclass(frozen=True)
class CushionProfile(CutProfile):
    """A superellipse: |x/a|^n + |y/b|^n = 1.

    Cushion sides genuinely bow OUTWARD -- GIA describes the cut as "curved
    sides", not a rounded rectangle -- and one exponent gives both the convex
    side and the rounded corner. It degrades to our existing ellipse at n = 2,
    so the family is continuous with oval rather than bolted beside it.

    INVENTED: `exponent`. No published corner radius or convexity figure exists
    for cushions; 3.0 reads as a modern cushion brilliant, and antique/old-mine
    stones are visibly plumper (nearer 2.5). Move it freely.
    """

    exponent: float = 3.0

    def _polyline(self, half_short, ratio, samples=_SAMPLES):
        p, q, e = half_short, half_short * ratio, 2.0 / self.exponent
        out = []
        for i in range(samples):
            t = TWO_PI * i / samples
            c, s = math.cos(t), math.sin(t)
            out.append((p * math.copysign(abs(c) ** e, c),
                        q * math.copysign(abs(s) ** e, s)))
        return out

    def corner_angles(self, ratio: float) -> list[float]:
        """Polar angles of the four rounded corners."""
        e = 2.0 / self.exponent
        out = []
        for k in range(4):
            t = math.pi / 4 + k * math.pi / 2
            c, s = math.cos(t), math.sin(t)
            out.append(_polar(math.copysign(abs(c) ** e, c),
                              ratio * math.copysign(abs(s) ** e, s)))
        return out

    def prong_layout(self, n):
        """Corners, not compass points.

        Stuller's production standards state the failure mode outright:
        "Cushions with rounded corners can easily rotate and fall out of a
        prong setting". Evenly-spaced angles is precisely what that warns
        against. CLAW rather than V -- the corner is rounded, not a vertex.
        """
        out = [(t, ProngType.CLAW) for t in self.corner_angles(
            self.default_ratio)]
        if n > 4:                       # long-side prongs at the widest points
            out += [(0.0, ProngType.CLAW), (math.pi, ProngType.CLAW)]
        return out[:n]


@dataclass(frozen=True)
class EmeraldProfile(CutProfile):
    """A true octagon: a rectangle with four truncated corners, straight sides.

    INVENTED: `corner_fraction`. No standards figure exists for how much of the
    width a corner truncation consumes. Beware the "0.227W" figure circulating
    in faceting sources -- that is the target P3 PAVILION FACET width during
    cutting (Jeff Graham, "Gram Easy Emerald"), not the plan-view corner, and
    reusing it would look cited and be wrong.

    The 45-degree corner face is a documented engineering assumption: it is the
    consistent trade convention, but no primary standard states it.
    """

    corner_fraction: float = 0.15

    def _corner(self, half_short: float) -> float:
        # Equal truncation on both axes puts the corner face at 45 degrees.
        return self.corner_fraction * 2 * half_short

    def _vertices(self, half_short, ratio):
        p, q = half_short, half_short * ratio
        c = min(self._corner(half_short), 0.9 * p, 0.9 * q)
        return [(p, q - c), (p - c, q), (-(p - c), q), (-p, q - c),
                (-p, -(q - c)), (-(p - c), -q), (p - c, -q), (p, -(q - c))]

    def _polyline(self, half_short, ratio, samples=_SAMPLES):
        vs = self._vertices(half_short, ratio)
        per_edge = max(samples // len(vs), 2)
        out = []
        for i, a in enumerate(vs):
            b = vs[(i + 1) % len(vs)]
            for k in range(per_edge):
                f = k / per_edge
                out.append((a[0] + f * (b[0] - a[0]), a[1] + f * (b[1] - a[1])))
        return out

    def corner_angles(self, ratio: float) -> list[float]:
        """Polar angles of the four corner-face midpoints."""
        vs = self._vertices(1.0, ratio)
        out = []
        for i in (0, 2, 4, 6):
            a, b = vs[i], vs[(i + 1) % len(vs)]
            out.append(_polar((a[0] + b[0]) / 2, (a[1] + b[1]) / 2))
        return out

    def segments(self, half_short, ratio):
        vs = self._vertices(half_short, ratio)
        return [LineSeg(vs[i], vs[(i + 1) % len(vs)]) for i in range(len(vs))]

    def prong_layout(self, n):
        """Prongs clasp the CUT CORNERS.

        Universal across the trade: the corner is the likeliest impact site and
        the only feature a prong can actually hook, while a prong on a flat side
        has nothing to grip and interrupts the cut's long straight lines. V --
        the corner is a genuine vertex, so the prong is notched to wrap it.
        """
        out = [(t, ProngType.V) for t in self.corner_angles(
            self.default_ratio)]
        if n > 4:                       # mid-points of the two long flat sides
            out += [(0.0, ProngType.CLAW), (math.pi, ProngType.CLAW)]
        return out[:n]


@dataclass(frozen=True)
class PearProfile(CutProfile):
    """A semicircular head, two straight tangent wings, one point.

    INVENTED: the belly position and the tangent-continuation wing. No published
    figure exists for either; the trade names only defects ("flat wings",
    "bulged wings", "high shoulders"). Tangent lines from the point to the head
    circle are the simplest construction that produces none of those, and they
    put the widest point at `1 / (2 * ratio)` of the length from the round end
    -- 31% at the conventional 1.6, which lands mid-band.
    """

    point_angle: float = _TIP_ANGLE

    def _geometry(self, half_short, ratio):
        p, q = half_short, half_short * ratio
        y0 = p - q                        # head centre; head bottom sits at -q
        d = q - y0                        # point-to-centre distance
        return p, q, y0, d

    def _polyline(self, half_short, ratio, samples=_SAMPLES):
        p, q, y0, d = self._geometry(half_short, ratio)
        # Tangent points: |T| = p and T . (T - P) = 0 about the head centre.
        ty = p * p / d
        tx = p * math.sqrt(max(1.0 - (p * p) / (d * d), 0.0))
        a0 = math.atan2(ty, tx)
        # CCW about the ORIGIN, which `point_at` / `angles_by_arc` rely on:
        # head the long way round the BOTTOM (-tangent -> +tangent), then up
        # the right wing to the point, then down the left wing. Sweeping the
        # head the other way crosses the top and makes polar angle
        # non-monotonic, which silently scrambles every arc-length lookup.
        a_start, sweep = math.pi - a0, math.pi + 2 * a0
        arc_n = max(samples * 2 // 3, 8)
        out = [(p * math.cos(a_start + sweep * i / arc_n),
                y0 + p * math.sin(a_start + sweep * i / arc_n))
               for i in range(arc_n + 1)]
        wing_n = max(samples // 6, 4)
        tip = (0.0, q)
        start = out[-1]                   # +tangent
        for k in range(1, wing_n + 1):    # +tangent -> point
            f = k / wing_n
            out.append((start[0] + f * (tip[0] - start[0]),
                        start[1] + f * (tip[1] - start[1])))
        end = (-tx, y0 + ty)              # -tangent, closing the loop
        for k in range(1, wing_n):        # point -> -tangent
            f = k / wing_n
            out.append((tip[0] + f * (end[0] - tip[0]),
                        tip[1] + f * (end[1] - tip[1])))
        return out

    def segments(self, half_short, ratio):
        p, q, y0, d = self._geometry(half_short, ratio)
        ty = p * p / d
        tx = p * math.sqrt(max(1.0 - (p * p) / (d * d), 0.0))
        a0 = math.atan2(ty, tx)
        return [
            ArcSeg((0.0, y0), p, math.pi - a0, TWO_PI + a0),
            LineSeg((tx, y0 + ty), (0.0, q)),
            LineSeg((0.0, q), (-tx, y0 + ty)),
        ]

    def prong_layout(self, n):
        """One V on the point, the rest shared by arc length.

        At n=4 the arc split lands the third prong exactly on the round end and
        mirrors the other two onto the shoulders, which is the layout the trade
        describes in words -- reached by construction rather than by inventing
        angles. Note the conventional pear is FIVE prongs (V plus two a side);
        4 and 6 are what `prong_count` currently allows.
        """
        return self._place_between(
            [(self.point_angle, ProngType.V)], n,
            1.0, self.default_ratio, ProngType.CLAW)


@dataclass(frozen=True)
class MarquiseProfile(CutProfile):
    """A navette: the intersection of two circular arcs, two points.

    For half-length a and half-width b the arc radius is R = (a^2 + b^2) / (2b)
    with centres on the SHORT axis at (-+(R - b), 0). The tip is a finite wedge,
    not a spike: theta = 2 atan(a / (R - b)) -- about 106 degrees at L:W 2.0 and
    exactly 120 at the vesica ratio sqrt(3), which is the one independent check
    on the whole construction.

    A documented engineering assumption rather than a certified standard: no
    gemological source confirms the two-arc outline, and real cutters may
    flatten the wings toward the tips, which would read pointier than this.
    """

    point_angles: tuple[float, ...] = (_TIP_ANGLE, -_TIP_ANGLE)

    def arc_radius(self, half_short: float, ratio: float) -> float:
        a, b = half_short * ratio, half_short
        return (a * a + b * b) / (2 * b)

    def tip_wedge_angle(self, ratio: float) -> float:
        r = self.arc_radius(1.0, ratio)
        return 2 * math.atan(ratio / (r - 1.0))

    def _polyline(self, half_short, ratio, samples=_SAMPLES):
        p, q = half_short, half_short * ratio
        r = self.arc_radius(half_short, ratio)
        cx = r - p                        # right arc centred at (-cx, 0)
        half = math.asin(min(q / r, 1.0))  # half the arc's angular sweep
        half_n = max(samples // 2, 8)
        out = []
        for i in range(half_n + 1):       # right arc, -q -> +q
            a = -half + 2 * half * i / half_n
            out.append((-cx + r * math.cos(a), r * math.sin(a)))
        for i in range(1, half_n):        # left arc, +q -> -q
            a = half - 2 * half * i / half_n
            out.append((cx - r * math.cos(a), r * math.sin(a)))
        return out

    def segments(self, half_short, ratio):
        p, q = half_short, half_short * ratio
        r = self.arc_radius(half_short, ratio)
        cx = r - p
        half = math.asin(min(q / r, 1.0))
        return [
            ArcSeg((-cx, 0.0), r, -half, half),
            ArcSeg((cx, 0.0), r, math.pi - half, math.pi + half),
        ]

    def prong_layout(self, n):
        """A V on each point, the rest shared by arc length between them.

        Both points get V-prongs -- stated as standard practice, and sold as
        stock findings ("Marquise V-Prong Basket"). The arc split puts the side
        prongs on the widest point by construction, which is where stock
        findings sit, though no source publishes the position.
        """
        return self._place_between(
            [(t, ProngType.V) for t in self.point_angles], n,
            1.0, self.default_ratio, ProngType.CLAW)


_PROFILES: dict[str, CutProfile] = {
    "round": RoundProfile("round", 1.0, 1.0, 1.0),
    "oval": OvalProfile("oval", 1.4, 1.0, 2.5),
    # Conventional L:W bands are well established across independent sources;
    # the defaults are the centre of each. GIA assigns NO cut grade to fancy
    # shapes (one is slated for 2027), so these are preference bands, not
    # standards -- we pick a default, we do not call it correct.
    "cushion": CushionProfile("cushion", 1.02, 1.0, 1.30),
    "emerald": EmeraldProfile("emerald", 1.40, 1.05, 1.75, has_vertices=True),
    "pear": PearProfile("pear", 1.60, 1.15, 2.10, has_vertices=True),
    "marquise": MarquiseProfile("marquise", 1.95, 1.50, 2.50,
                                has_vertices=True),
}

CUT_NAMES: tuple[str, ...] = tuple(_PROFILES)


def profile_for(shape: str) -> CutProfile:
    """The `CutProfile` for a RingSpec `stones.shape`."""
    try:
        return _PROFILES[shape]
    except KeyError:
        raise ValueError(
            f"unknown stone shape {shape!r}; supported: "
            f"{', '.join(CUT_NAMES)}"
        ) from None
