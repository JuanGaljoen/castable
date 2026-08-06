"""Castability validation — distinct from schema validation (RNG-14, AC3).

Schema validation (models.py) only checks structural validity; a well-formed
spec can still be physically uncastable. `validate_castability` runs the
lost-wax manufacturing gate on a schema-valid spec and returns structured
`Violation`s *before* any geometry runs. An empty list means castable.

Casting constants are single-sourced from ringcad.mesh_validator (the same
limits the post-generation mesh check uses) — never duplicated here.
"""
from __future__ import annotations

import math

from pydantic import BaseModel

from ringcad.mesh_validator import MIN_PRONG_TIP_MM, MIN_WALL_MM

from .models import (
    SHANK_THICKNESS_TAPER, HaloSpec, RingSpec, SideStoneSpec, TrilogySpec,
    HALO_WELL_BACK_RATIO, channel_band_width, channel_groove_depth,
    halo_min_arc,
)

# Side-stone row: angular clearance off the centre head (A_START) and the
# angular limit before the ring base (A_MAX) — mirrored by the actual
# placement math in ringcad/geometry/side_stone.py (CP2). The 100 degree
# budget between them leaves >= 70 degrees clear of the base on each side, so
# the ring stays resizable.
_SIDE_STONE_A_START_DEG = 10.0
_SIDE_STONE_A_MAX_DEG = 110.0

# Fraction of the inter-prong seat arc that becomes prong wire. The prong-tip
# diameter is a coarse proxy (plan Risk #2, "fuzzy") pending an RNG-15 pin
# against the SCAD/build123d geometry; do not treat it as exact.
_PRONG_WIRE_FRACTION = 0.25

# Section radius of the seat collar, mirrored from ringcad/geometry/seat.py
# (`max(MIN_WALL / 2, 0.45)`). Imported as a number rather than from the geometry
# package so the spec layer stays independent of the kernel, exactly as the
# side-stone placement angles above mirror side_stone.py.
_SEAT_COLLAR_R = max(MIN_WALL_MM / 2, 0.45)


class Violation(BaseModel):
    """A single structured castability failure (JSON-serializable)."""

    code: str
    field: str | None
    message: str
    limit_mm: float | None
    actual_mm: float | None
    severity: str = "error"


def _min_wall(spec: RingSpec) -> list[Violation]:
    """Walls below MIN_WALL_MM (0.8 inclusive passes)."""
    checks = (
        ("shank.band_thickness", spec.shank.band_thickness),
        ("shank.band_width", spec.shank.band_width),
        ("setting.setting_height", spec.setting.setting_height),
    )
    out: list[Violation] = []
    for field, value in checks:
        if value < MIN_WALL_MM:
            out.append(
                Violation(
                    code="min_wall",
                    field=field,
                    message=f"{field} {value}mm is below the {MIN_WALL_MM}mm "
                    "minimum wall thickness for lost-wax casting.",
                    limit_mm=MIN_WALL_MM,
                    actual_mm=value,
                )
            )
    return out


def _min_prong_tip(spec: RingSpec) -> list[Violation]:
    """Derived prong-tip diameter below MIN_PRONG_TIP_MM (coarse proxy)."""
    arc = math.pi * spec.stones.stone_diameter / spec.setting.prong_count
    tip = arc * _PRONG_WIRE_FRACTION
    if tip < MIN_PRONG_TIP_MM:
        return [
            Violation(
                code="min_prong_tip",
                field="setting.prong_count",
                message=f"Derived prong-tip diameter {tip:.3f}mm is below the "
                f"{MIN_PRONG_TIP_MM}mm minimum for {spec.setting.prong_count} "
                "prongs at this stone size.",
                limit_mm=MIN_PRONG_TIP_MM,
                actual_mm=tip,
            )
        ]
    return []


def _geometric(spec: RingSpec) -> list[Violation]:
    """Cross-field geometric impossibilities."""
    out: list[Violation] = []
    # The stone's LONGEST axis is what has to fit over the bore: `stone_diameter`
    # is the short axis once a shape is involved (RNG-23), so comparing it alone
    # let a 10mm stone at length_ratio 2.5 -- 25mm long across a 16.5mm bore --
    # through the gate.
    stone_length = spec.stones.stone_diameter * getattr(
        spec.stones, "length_ratio", 1.0
    )
    if stone_length >= spec.shank.inner_diameter:
        out.append(
            Violation(
                code="stone_exceeds_bore",
                field="stones.stone_diameter",
                message="Stone must be smaller than the finger bore "
                "(inner_diameter) along its longest axis.",
                limit_mm=spec.shank.inner_diameter,
                actual_mm=stone_length,
            )
        )
    if spec.stones.stone_height >= spec.setting.setting_height:
        out.append(
            Violation(
                code="stone_exceeds_head",
                field="stones.stone_height",
                message="Stone height must be smaller than the setting height.",
                limit_mm=spec.setting.setting_height,
                actual_mm=spec.stones.stone_height,
            )
        )
    return out


# RNG-9 CP4 note: `_halo_wall` (halo_gap >= MIN_WALL_MM) and `_halo_accent_tip`
# (min(dia, height) * _ACCENT_TIP_FRACTION >= MIN_PRONG_TIP_MM) were removed
# here. Both were CP1-era coarse proxies over spec FIELDS, explicitly flagged
# "fuzzy... pending a pin against real geometry" — written before CP2/CP3 built
# the real gallery/accent-seat/accent-prong geometry. That geometry is castable
# BY CONSTRUCTION (gallery's rail/bridge walls are sized from fixed minima, not
# derived from `halo_gap`; accent seat/prong walls similarly), proven across the
# full field range by tests/test_halo_watertight.py's BAND + the CP2/CP3
# in-kernel self-checks (check_gallery/check_accent_seat/check_accent_prong).
# The two proxies rejected the RNG-9 golden-halo DEFAULTS
# (halo_gap=0.5, halo_stone_diameter=1.3/height=1.2) that CP3 proved clean,
# which would 400 the endpoint's own documented golden example. `_halo_overcrowding`
# stays: it catches a genuine cross-field impossibility (arc spacing between
# accents) that construction does not guard against.


def _ring_perimeter(semi_minor: float, semi_major: float) -> float:
    """Perimeter of the accent ring, circle or ellipse.

    Ramanujan's approximation, accurate to better than 1e-5 relative across the
    elongations RingSpec allows. Kept as arithmetic here rather than reaching into
    `ringcad.geometry.outline`, so the spec layer stays independent of the kernel
    (the same separation `_SEAT_COLLAR_R` and the side-stone angles observe).
    """
    if semi_minor == semi_major:
        return 2 * math.pi * semi_minor
    a, b = semi_major, semi_minor
    return math.pi * (
        3 * (a + b) - math.sqrt((3 * a + b) * (a + 3 * b))
    )


def _halo_overcrowding(spec: RingSpec) -> list[Violation]:
    """Accents packed tighter than their own diameter around the halo ring.

    Measured around the ring the halo ACTUALLY rides. Since RNG-23 CP3 that ring
    follows the centre stone's outline, so for an oval stone it is an ellipse and
    is longer than a circle of the short axis. Computing the arc from that circle
    rejected specs the geometry could build -- caught by running a real oval-halo
    photo end to end, since every classify test stubs the client.
    """
    if not isinstance(spec, HaloSpec):
        return []
    halo = spec.halo
    offset = halo.halo_gap + halo.halo_stone_diameter / 2
    semi_minor = spec.stones.stone_diameter / 2
    semi_major = semi_minor * getattr(spec.stones, "length_ratio", 1.0)
    perimeter = _ring_perimeter(semi_minor + offset, semi_major + offset)
    arc = perimeter / halo.halo_stone_count
    if arc < halo.halo_stone_diameter:
        return [
            Violation(
                code="halo_overcrowding",
                field="halo.halo_stone_count",
                message=f"{halo.halo_stone_count} accents leave {arc:.3f}mm of arc "
                f"each, below the {halo.halo_stone_diameter}mm accent diameter.",
                limit_mm=halo.halo_stone_diameter,
                actual_mm=arc,
            )
        ]
    return []


def _halo_web(spec: RingSpec) -> list[Violation]:
    """Metal left BETWEEN adjacent halo seats (RNG-19 CP4).

    `_halo_overcrowding` guards that accents do not overlap each other. This
    guards what survives between them — the web the seats are bored either side
    of. They are different questions, and only the first was ever asked: the
    corpus halo passed the gate with a 0.195mm web, a quarter of the casting
    floor, because 22 accents of 1.2mm on that ring leave arc for the stones and
    almost nothing for the metal.

    Measured in arc, matching `_halo_overcrowding`'s own convention rather than
    the chord the side-stone check uses. The two diverge by <0.5% at these
    counts (~0.004mm against a 0.8mm floor), so consistency with the halo's
    existing math is worth more here than the stricter measure.
    """
    if not isinstance(spec, HaloSpec):
        return []
    halo = spec.halo
    offset = halo.halo_gap + halo.halo_stone_diameter / 2
    semi_minor = spec.stones.stone_diameter / 2
    semi_major = semi_minor * getattr(spec.stones, "length_ratio", 1.0)
    perimeter = _ring_perimeter(semi_minor + offset, semi_major + offset)
    arc = perimeter / halo.halo_stone_count
    needed = halo_min_arc(
        halo.halo_stone_diameter, MIN_WALL_MM, MIN_PRONG_TIP_MM
    )
    if arc < needed:
        web = arc - halo.halo_stone_diameter * HALO_WELL_BACK_RATIO
        return [
            Violation(
                code="halo_web",
                field="halo.halo_stone_count",
                message=f"{halo.halo_stone_count} accents leave {web:.3f}mm of "
                f"metal between adjacent seats, below the {MIN_WALL_MM}mm "
                f"minimum wall; at most {int(perimeter // needed)} accents fit.",
                limit_mm=needed,
                actual_mm=arc,
            )
        ]
    return []


def _trilogy_overcrowding(spec: RingSpec) -> list[Violation]:
    """Side stone placed close enough to collide with the centre stone.

    Not a wall-thickness proxy (docs/adr/0003): `side_stone_gap` is a
    PLACEMENT field, not a wall field — the side setting's post wall (CP2) is
    a fixed construction margin, independent of it, exactly like the gallery
    rail wall was independent of `halo_gap` (docs/adr/0002). This checks a
    genuine geometric fact instead — the side stone's angular placement is
    derived from an ARC-LENGTH approximation of the gap, but the two stones'
    actual separation is the CHORD (straight-line) distance, which is always
    <= that arc. At large offsets the two diverge enough that the girdles can
    overlap even though `side_stone_gap` is positive.
    """
    if not isinstance(spec, TrilogySpec):
        return []
    trilogy = spec.trilogy
    shank = spec.shank
    # Width-consumer, not curve-walker: the side stones flank along the band,
    # which is the SAME axis an N-S oval is longest on, so the clearance must be
    # measured from the long half-width. Round is length_ratio 1.0, unchanged.
    stone_r = (spec.stones.stone_diameter / 2) * getattr(
        spec.stones, "length_ratio", 1.0
    )
    side_r = trilogy.side_stone_diameter / 2
    # THICKNESS taper, not `shank.shank_taper` (which is the WIDTH flare): the
    # head radius is how far the band's outer surface stands off the finger, and
    # the builder derives it the same way (`_common._clamps`). Reading the width
    # field here is what made this check disagree with the geometry it guards.
    head_r = shank.inner_diameter / 2 + shank.band_thickness * SHANK_THICKNESS_TAPER
    arc = stone_r + trilogy.side_stone_gap + side_r
    phi = arc / head_r
    chord = 2 * head_r * math.sin(phi / 2)
    min_clearance = stone_r + side_r
    if chord < min_clearance:
        return [
            Violation(
                code="trilogy_overcrowding",
                field="trilogy.side_stone_gap",
                message=f"Side stone placement leaves {chord:.3f}mm of clearance "
                f"to the centre stone, below the {min_clearance:.3f}mm needed "
                "for the two stones' girdles not to overlap.",
                limit_mm=min_clearance,
                actual_mm=chord,
            )
        ]
    return []


def _side_stone_overcrowding(spec: RingSpec) -> list[Violation]:
    """Accent row overruns the shoulder span, or adjacent accents collide.

    Not a wall-thickness proxy (docs/adr/0003): the channel-wall thickness
    (CP2) is a fixed construction margin, independent of `accent_gap`,
    exactly like the trilogy post / gallery rail are independent of their own
    gap fields. Checks two real placement facts instead:

      (a) the row must fit between A_START (clears the centre head) and
          A_MAX (stays off the ring base) — compared in arc-length mm so the
          Violation stays unit-consistent with every other check here, not in
          degrees. Flags `accent_count_per_side`.
      (b) adjacent accents' true CHORD (straight-line) distance at the band's
          outer radius must clear their combined diameter — the same
          arc-vs-chord divergence `_trilogy_overcrowding` guards against.
          Flags `accent_gap`.

    Returns on the first violation found, (a) then (b), matching the shape of
    `_halo_overcrowding`/`_trilogy_overcrowding`.
    """
    if not isinstance(spec, SideStoneSpec):
        return []
    ss = spec.side_stone
    shank = spec.shank
    band_outer_r = shank.inner_diameter / 2 + shank.band_thickness
    step = ss.accent_stone_diameter + ss.accent_gap
    dphi = math.degrees(step / band_outer_r)

    budget_deg = _SIDE_STONE_A_MAX_DEG - _SIDE_STONE_A_START_DEG
    budget_arc = band_outer_r * math.radians(budget_deg)
    required_arc = (ss.accent_count_per_side - 1) * step
    if required_arc > budget_arc:
        return [
            Violation(
                code="side_stone_overcrowding",
                field="side_stone.accent_count_per_side",
                message=f"{ss.accent_count_per_side} accents per side need "
                f"{required_arc:.3f}mm of shoulder arc, above the "
                f"{budget_arc:.3f}mm available before the ring base.",
                limit_mm=budget_arc,
                actual_mm=required_arc,
            )
        ]

    chord = 2 * band_outer_r * math.sin(math.radians(dphi) / 2)
    min_clearance = ss.accent_stone_diameter
    if chord < min_clearance:
        return [
            Violation(
                code="side_stone_overcrowding",
                field="side_stone.accent_gap",
                message=f"Adjacent accents leave {chord:.3f}mm of clearance, "
                f"below the {min_clearance:.3f}mm needed for their girdles "
                "not to overlap.",
                limit_mm=min_clearance,
                actual_mm=chord,
            )
        ]
    return []


def _stone_curvature(spec: RingSpec) -> list[Violation]:
    """The girdle bends too sharply for the seat collar to follow it (RNG-23).

    A tube of section radius r swept along a curve whose radius of curvature is
    smaller than r self-intersects: the inner wall passes through itself. That is
    degenerate metal, not merely thin metal, so it is checked as the geometric
    fact it is rather than through a wall-thickness proxy (cf. docs/adr/0002,
    0003).

    For an ellipse with semi-axes p (short) and q (long) the tightest bend is at
    the apex of the long axis, radius p^2/q. With `stone_diameter` as the short
    axis this is simply `(stone_diameter / 2) / length_ratio`, so it tightens
    both as the stone shrinks and as it elongates.
    """
    stones = getattr(spec, "stones", None)
    if stones is None or getattr(stones, "shape", "round") == "round":
        return []
    ratio = getattr(stones, "length_ratio", 1.0)
    if ratio <= 1.0:
        return []
    semi_minor = stones.stone_diameter / 2
    min_curvature = semi_minor / ratio
    if min_curvature >= _SEAT_COLLAR_R:
        return []
    return [
        Violation(
            code="stone_curvature",
            field="stones.length_ratio",
            message=(
                f"The stone's tip curves with a {min_curvature:.3f}mm radius, "
                f"tighter than the {_SEAT_COLLAR_R:.2f}mm seat collar can "
                "follow without passing through itself. Reduce length_ratio or "
                "increase stone_diameter."
            ),
            limit_mm=_SEAT_COLLAR_R,
            actual_mm=min_curvature,
        )
    ]


def _side_stone_channel(spec: RingSpec) -> list[Violation]:
    """The band must be able to HOLD a channel (RNG-19 CP3).

    Channel setting cuts a groove into the band, so unlike the retention modes
    that sit on the surface it consumes the band's own metal on two axes:

      (a) WIDTH — the groove runs across the band's width, so the band must
          carry the stone plus a MIN_WALL wall each side. This is the
          arithmetic that made RNG-11 ship raised beads: a 1.5mm accent needs
          3.1mm of band and real specs supply 2.0mm.
      (b) THICKNESS — the groove is cut inward from the outer surface, so the
          metal left under it must still clear MIN_WALL. Otherwise the cut
          severs the band, and per docs/adr/0005 a severed band can still
          report watertight.

    Both are hard geometry, not preference: no construction satisfies them on a
    band that is simply too small. Returns (a) then (b), matching the shape of
    the overcrowding checks.
    """
    if not isinstance(spec, SideStoneSpec):
        return []
    ss = spec.side_stone
    shank = spec.shank

    needed_w = channel_band_width(ss.accent_stone_diameter, MIN_WALL_MM)
    if shank.band_width < needed_w:
        return [
            Violation(
                code="side_stone_channel_fit",
                field="shank.band_width",
                message=f"a {ss.accent_stone_diameter:.2f}mm channel accent "
                f"needs a {needed_w:.3f}mm band (stone + {MIN_WALL_MM}mm wall "
                f"each side); this band is {shank.band_width:.3f}mm.",
                limit_mm=needed_w,
                actual_mm=shank.band_width,
            )
        ]

    depth = channel_groove_depth(ss.accent_stone_height)
    needed_t = depth + MIN_WALL_MM
    if shank.band_thickness < needed_t:
        return [
            Violation(
                code="side_stone_channel_floor",
                field="shank.band_thickness",
                message=f"a {ss.accent_stone_height:.2f}mm accent cuts a "
                f"{depth:.3f}mm groove, needing a {needed_t:.3f}mm band to "
                f"leave {MIN_WALL_MM}mm of floor; this band is "
                f"{shank.band_thickness:.3f}mm.",
                limit_mm=needed_t,
                actual_mm=shank.band_thickness,
            )
        ]
    return []


def validate_castability(spec: RingSpec) -> list[Violation]:
    """Run the full lost-wax gate; [] means the spec is castable."""
    return (
        _min_wall(spec)
        + _min_prong_tip(spec)
        + _geometric(spec)
        + _stone_curvature(spec)
        + _halo_overcrowding(spec)
        + _halo_web(spec)
        + _trilogy_overcrowding(spec)
        + _side_stone_overcrowding(spec)
        + _side_stone_channel(spec)
    )


def is_castable(spec: RingSpec) -> bool:
    """True iff the spec produces no castability violations."""
    return not validate_castability(spec)
