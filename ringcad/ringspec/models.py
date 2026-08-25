"""RingSpec v1 Pydantic models — the versioned, typed contract (RNG-14).

Pydantic enforces ONLY structural validity: types, prong_count in {4, 6},
gt=0, generous physical caps, extra="forbid", and the version/archetype
literals. Casting FLOORS (min wall 0.8mm, min tip 0.7mm) live exclusively in
`castability.validate_castability` so a well-formed-but-uncastable spec can be
constructed and then flagged (a vision layer can emit such specs). The element
groups (shank/setting/stones/motifs) map onto the build123d modules proven in
RNG-13 so RNG-15 consumes RingSpec directly.
"""
from __future__ import annotations

from typing import Annotated, Literal, Union

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    TypeAdapter,
    ValidationError,
    model_validator,
)

SPEC_VERSION = "1.0"

# Generous physical caps — structural sanity only, NOT casting floors. The
# lower casting floors (min wall / min tip) are enforced in castability.py.


# RNG-19: the shank tapers in WIDTH toward the head; thickness stays
# near-constant so the ring keeps a consistent feel on the finger
# (docs/jewelry-design-principles.md). One factor applied to both axes made the
# band a swollen tube at the head.
#
# These live here, in the schema, rather than in `geometry/_common.py`, because
# BOTH the builder and `castability.py` derive `head_r` from the thickness
# taper. `ringspec` cannot import `geometry` (the dependency runs the other
# way), so a geometry-side constant would force the check to keep its own copy —
# exactly the drift docs/adr/0002 is about, and exactly what had already
# happened: the builder used a module constant while the check read the
# `shank_taper` FIELD.
SHANK_WIDTH_TAPER = 1.35
SHANK_THICKNESS_TAPER = 1.15

# --- Channel setting (RNG-19 CP3) -------------------------------------------
# Here for the same reason as the tapers above: `castability` derives the band's
# wall/floor requirements from the groove, `geometry` cuts it, and the two must
# read one definition.
#
# A channel holds stones in a groove between two walls, with bearings cut into
# the walls' inner faces (docs/jewelry-design-principles.md #Channel). We render
# metal only, so the row IS the negative of its stones: the groove is cut at the
# CLEAR span and each stone is then cut at its full diameter, which bites
# GIRDLE_PENETRATION into either wall and leaves the bearings for free.
GIRDLE_PENETRATION = 0.2  # how far each girdle edge tucks into its wall
GIRDLE_RECESS = 0.2       # how far the girdle sits below the band's surface
PAVILION_FRACTION = 0.65  # share of a stone's height below its girdle


def channel_groove_depth(accent_stone_height: float) -> float:
    """Radial depth of the channel trench, measured in from the band's outer
    surface: the stone's pavilion plus the girdle's recess below the surface."""
    return PAVILION_FRACTION * accent_stone_height + GIRDLE_RECESS


# --- Halo plate (RNG-19 CP4) ------------------------------------------------
# The halo body is ONE continuous plate with the accent seats bored through it
# (docs/reference/halo.png), not a ring of collar tubes. Metal outside the
# outermost bore, giving the plate the crisp rim the sketch shows.
#
# 0.5mm is the TRADE FIGURE, not a taste call: "you will need at least 0.5mm
# extra on each side of the stone to account for the bright cut"
# (ganoksin.com/article/step-step-guide-single-row-pave-settings). Below MIN_WALL
# legitimately, because this is how far the plate overhangs its outermost seat,
# NOT a wall thickness -- the plate's actual wall is its THICKNESS, which carries
# the structural floor.
#
# It has been wrong in BOTH directions. 0.8mm (MIN_WALL, applied out of caution)
# read as a broad flat collar of dead metal; 0.25mm was then picked by eye off
# "that looks beefy" and undershot the trade minimum by half. Looked up rather
# than eyeballed on the third attempt.
HALO_PLATE_RIM = 0.5
# How far the plate reaches INSIDE the centre girdle, so the centre setting's
# claws are embedded in it rather than grazing its edge. The claws rise through
# the plate's own height exactly at the girdle radius, so without this the two
# only touch -- and the halo needed a hub-and-spokes gallery of its own to hang
# from, which read as a cross slung under it. Larger than the claw wire radius
# (0.5) so the weld is volumetric.
HALO_PLATE_INNER_BITE = 0.7
# Bore radius at the bottom of a seat, as a fraction of the stone's: a seat is a
# TAPERED bearing, narrower behind the girdle than at it.
HALO_WELL_BACK_RATIO = 0.5


# Shallowest seat worth boring; below this there is no bearing left to speak of.
HALO_MIN_SEAT_DEPTH = 0.2


def halo_seat_depth(
    accent_stone_height: float, available: float, min_wall: float
) -> float:
    """How deep a seat can actually be bored.

    The stone's pavilion, CLAMPED to the metal there is to bore into: a plate
    needs `depth + min_wall`, and it only has `available` (the setting's
    half-height) before it drops below the placement origin into the shank. A
    3mm accent in a 3mm setting asked for a 2.75mm plate inside 1.5mm of room
    and pushed the halo through the band — OCC then failed to bound the solid at
    all. Shallower seats on a low setting is the physical answer: you cannot
    bore deeper than the metal you have.
    """
    return max(HALO_MIN_SEAT_DEPTH,
               min(PAVILION_FRACTION * accent_stone_height, available - min_wall))


def halo_plate_thickness(accent_stone_height: float, min_wall: float) -> float:
    """Plate thickness: the seat's own depth plus a floor beneath it.

    The seats are BLIND, and that is a structural requirement rather than a
    style choice. The accent ring and the gallery rail share a radius, so a seat
    bored through the plate lands straight on the rail torus, and cone-against-
    torus intersections would not tessellate — a valid single B-rep solid whose
    mesh had null-triangulation faces and was not watertight. Leaving MIN_WALL of
    floor keeps every bore clear of the rail entirely.
    """
    return PAVILION_FRACTION * accent_stone_height + min_wall


def halo_min_arc(
    accent_stone_diameter: float, min_wall: float, min_prong_tip: float
) -> float:
    """Arc each accent needs so the METAL BETWEEN adjacent seats survives.

    `_halo_overcrowding` only ever checked that accents do not overlap each
    other (`arc >= diameter`). It never checked what is left between them, so a
    halo could pass the gate with 0.195mm webs and report castable — exactly
    docs/adr/0006, a wrong gate being silent.

    **Measured where the bore is NARROWEST, not at the girdle.** The seats are
    tapered, so the metal between two of them is a V-shaped ridge: near zero at
    the surface, thickening with depth. Measuring at the girdle — the bore's
    widest point — treats that ridge's top sliver as the wall, and it forced
    1.1mm of flat plate between every pair of stones. Real halos set the stones
    nearly touching, with a bright-cut edge and a bead between them
    (docs/reference/halo.png); the load-bearing section is the one lower down,
    where the bores have tapered in to `HALO_WELL_BACK_RATIO` of their radius.

    So the wall is `pitch - 2*back_r`, and requiring that to clear `min_wall`
    gives `pitch >= accent_r + min_wall`. `min_prong_tip` is retained in the
    signature because the bead still has to exist, but it no longer sets the
    spacing: beads are fused ON the bored plate, overhanging the seat rims the
    way a set bead does, rather than needing clear plate to stand on.
    """
    back_r = accent_stone_diameter / 2 * HALO_WELL_BACK_RATIO
    # Never below the stone's own diameter: on a big accent the wall rule is
    # slacker than simply not overlapping the neighbour, and `_halo_overcrowding`
    # owns that floor -- but this must not report a limit it would itself allow.
    return max(accent_stone_diameter, min_wall + 2 * back_r)


def channel_band_width(accent_stone_diameter: float, min_wall: float) -> float:
    """Band width a channel needs: the stone plus a wall each side. This is the
    arithmetic that made RNG-11 ship raised beads instead — a 1.5mm accent needs
    3.1mm of band and the corpus spec supplies 2.0mm."""
    return accent_stone_diameter + 2 * min_wall


class Shank(BaseModel):
    """Band geometry. `shank_taper` is the WIDTH flare toward the head (the SCAD
    8th shaping param); thickness is governed by `SHANK_THICKNESS_TAPER`."""

    model_config = ConfigDict(extra="forbid")

    inner_diameter: float = Field(gt=0, le=40)
    band_width: float = Field(gt=0, le=12)
    band_thickness: float = Field(gt=0, le=8)
    shank_taper: float = Field(default=SHANK_WIDTH_TAPER, ge=1.0, le=3.0)


class Setting(BaseModel):
    """Prong/gallery group. prong_count is a strict 4-or-6 literal."""

    model_config = ConfigDict(extra="forbid")

    prong_count: Literal[4, 6]
    setting_height: float = Field(gt=0, le=20)


class Stones(BaseModel):
    """Centre-stone sizing and shape for the seat module.

    `stone_diameter` is the SHORT axis (the width); the long axis is
    `stone_diameter * length_ratio`. Both shape fields are defaulted, so every
    spec written before RNG-23 stays valid and still means a round stone.

    A ratio rather than an explicit length: it is the quantity a photo actually
    shows (feeding RNG-26), and `length_ratio == 1.0` makes round fall out of the
    same code path instead of needing a branch. The 2.5 cap is a castability
    guard -- an ellipse's tightest bend is `semi_minor^2 / semi_major`, so
    elongation directly thins the metal at the tips.
    """

    model_config = ConfigDict(extra="forbid")

    stone_diameter: float = Field(gt=0, le=24)
    stone_height: float = Field(gt=0, le=12)
    shape: Literal["round", "oval", "cushion", "emerald", "pear",
                   "marquise"] = "round"
    length_ratio: float = Field(default=1.0, ge=1.0, le=2.5)

    @model_validator(mode="after")
    def _ratio_within_the_cuts_band(self):
        """Hold `length_ratio` inside its cut's own band, BOTH ways (RNG-33).

        Per-cut proportions are mandatory, not cosmetic: the conventional L:W
        is ~1.02 for cushion, 1.40 emerald, 1.60 pear, 1.95 marquise, so a
        single shared default of 1.0 makes three of the four wrong on sight.

        **Below the band, fill with the cut's default.** Only cuts whose band
        STARTS above 1.0 are filled. A marquise at 1.0 is a circle, not a
        marquise -- there is no meaningful stone there, so this is a repair
        rather than a surprise. Cushion and oval both legitimately reach 1.0 (a
        square cushion is 1.00; an oval at 1.0 IS a circle, which is RNG-23's
        contract) and are left exactly alone.

        **Above the band, clamp to its ceiling** (CP4). This half was missing,
        and the asymmetry was the real identity hole -- not the one the frozen
        spec anticipated. The spec expected REPAIR to break identity, by scaling
        `length_ratio` down for a `stone_curvature` violation until a marquise
        rendered as a lens; measured over 7500 in-band specs, repair moves the
        ratio 12 times and never once out of band, because CP1's
        `_stone_curvature` returns early on any cut `has_vertices` and so cannot
        fire on emerald, pear or marquise at all. Nothing was guarding the INPUT
        instead: a `cushion` at 2.38 validated, built, and was called a cushion.

        Clamping silently is the deliberate choice, for symmetry with the fill
        above -- a value that is not the cut is corrected the same way at either
        end, rather than being repaired at one end and refused at the other.
        These are preference bands, not standards (GIA assigns no cut grade to
        fancy shapes), so the honest framing is "that is not what this cut is
        called", not "that stone is invalid".
        """
        from .cuts import profile_for
        profile = profile_for(self.shape)
        if self.length_ratio < profile.min_ratio:
            object.__setattr__(self, "length_ratio", profile.default_ratio)
        elif self.length_ratio > profile.max_ratio:
            object.__setattr__(self, "length_ratio", profile.max_ratio)
        return self


class Motif(BaseModel):
    """Decorative element placeholder (empty list is valid for a solitaire)."""

    model_config = ConfigDict(extra="forbid")

    kind: str
    position: float | None = None


class FieldConfidence(BaseModel):
    """Per-field vision confidence (0..1). RNG-12 populates; None until then."""

    model_config = ConfigDict(extra="forbid")

    inner_diameter: float | None = Field(default=None, ge=0, le=1)
    band_width: float | None = Field(default=None, ge=0, le=1)
    band_thickness: float | None = Field(default=None, ge=0, le=1)
    stone_diameter: float | None = Field(default=None, ge=0, le=1)
    stone_height: float | None = Field(default=None, ge=0, le=1)
    prong_count: float | None = Field(default=None, ge=0, le=1)
    setting_height: float | None = Field(default=None, ge=0, le=1)


class SolitaireSpec(BaseModel):
    """Solitaire archetype: one centre stone in a prong setting on a shank."""

    model_config = ConfigDict(extra="forbid")

    version: Literal["1.0"] = "1.0"
    archetype: Literal["solitaire"] = "solitaire"
    shank: Shank
    setting: Setting
    stones: Stones
    motifs: list[Motif] = Field(default_factory=list)
    confidence: FieldConfidence | None = None


class Halo(BaseModel):
    """Accent-stone ring encircling the centre stone (RNG-9).

    How many accents actually fit depends on the centre stone the halo rides,
    not on this range alone: each seat needs metal either side of it. That is
    `_halo_web`'s job (RNG-19 CP4), not the schema's.
    """

    model_config = ConfigDict(extra="forbid")

    halo_stone_diameter: float = Field(default=1.3, ge=0.9, le=2.5)
    halo_stone_count: int = Field(default=14, ge=8, le=24)
    halo_gap: float = Field(default=0.5, ge=0.3, le=1.5)
    halo_stone_height: float = Field(default=1.2, ge=0.8, le=3.0)


class HaloSpec(BaseModel):
    """Halo archetype: a solitaire centre plus a ring of accent stones."""

    model_config = ConfigDict(extra="forbid")

    version: Literal["1.0"] = "1.0"
    archetype: Literal["halo"] = "halo"
    shank: Shank
    setting: Setting
    stones: Stones
    halo: Halo
    motifs: list[Motif] = Field(default_factory=list)
    confidence: FieldConfidence | None = None


class Trilogy(BaseModel):
    """Side-stone group flanking the centre stone (RNG-10)."""

    model_config = ConfigDict(extra="forbid")

    side_stone_diameter: float = Field(default=2.5, ge=0.9, le=6.0)
    side_stone_height: float = Field(default=1.8, ge=0.8, le=4.0)
    side_stone_gap: float = Field(default=0.6, ge=0.3, le=2.0)


class TrilogySpec(BaseModel):
    """Trilogy archetype: a solitaire centre plus two symmetric side stones."""

    model_config = ConfigDict(extra="forbid")

    version: Literal["1.0"] = "1.0"
    archetype: Literal["trilogy"] = "trilogy"
    shank: Shank
    setting: Setting
    stones: Stones
    trilogy: Trilogy
    motifs: list[Motif] = Field(default_factory=list)
    confidence: FieldConfidence | None = None


class SideStone(BaseModel):
    """Channel-set accent row down each shoulder of the shank (RNG-11).

    `retention` is a Literal["channel"] in v1 — pave is a future value; a
    "pave" spec is a clean schema rejection today, not a shipped-but-broken
    option (specs/RNG-11.md Decision 5).
    """

    model_config = ConfigDict(extra="forbid")

    accent_stone_diameter: float = Field(default=1.5, ge=0.9, le=2.5)
    accent_stone_height: float = Field(default=1.2, ge=0.8, le=3.0)
    accent_count_per_side: int = Field(default=3, ge=1, le=8)
    accent_gap: float = Field(default=0.3, ge=0.2, le=1.0)
    retention: Literal["channel"] = "channel"


class SideStoneSpec(BaseModel):
    """Side-stone archetype: a solitaire centre plus a channel-set accent row
    down each shoulder."""

    model_config = ConfigDict(extra="forbid")

    version: Literal["1.0"] = "1.0"
    archetype: Literal["side_stone"] = "side_stone"
    shank: Shank
    setting: Setting
    stones: Stones
    side_stone: SideStone
    motifs: list[Motif] = Field(default_factory=list)
    confidence: FieldConfidence | None = None


ARCHETYPE_TAGS = {"solitaire", "halo", "trilogy", "side_stone"}

# The versioned contract is a discriminated (tagged) union over `archetype`.
# `RingSpec` is an Annotated alias — a type hint, NOT an instantiable class;
# construct a concrete member (SolitaireSpec/HaloSpec/TrilogySpec/
# SideStoneSpec) or route dict/JSON input through validate_spec (which uses
# the adapter below).
RingSpec = Annotated[
    Union[SolitaireSpec, HaloSpec, TrilogySpec, SideStoneSpec],
    Field(discriminator="archetype"),
]
_RING_SPEC_ADAPTER = TypeAdapter(RingSpec)


def validate_spec(data: object) -> SolitaireSpec | HaloSpec:
    """Validate input into the concrete archetype member, raising on failure.

    Back-compat: an archetype-less dict defaults to "solitaire" (the union
    rejects a missing tag with union_tag_not_found), without mutating caller
    input.
    """
    if isinstance(data, dict) and "archetype" not in data:
        data = {**data, "archetype": "solitaire"}
    return _RING_SPEC_ADAPTER.validate_python(data)


def spec_errors(exc: ValidationError) -> list[dict]:
    """Flatten a ValidationError into JSON-serializable field-level errors.

    Each entry is {"field", "reason", "type"}. The leading archetype tag is
    stripped from the loc path; an invalid/missing tag names "archetype"; a
    None/empty body names "" ("" == top-level). Disambiguation is on error
    TYPE, not loc, so a tag error never collides with a body error.
    """
    out: list[dict] = []
    for err in exc.errors():
        etype = str(err["type"])
        loc = err["loc"]
        if etype in ("union_tag_invalid", "union_tag_not_found"):
            field = "archetype"
        elif not loc:
            field = ""
        elif loc[0] in ARCHETYPE_TAGS:
            field = ".".join(str(part) for part in loc[1:])
        else:
            field = ".".join(str(part) for part in loc)
        out.append(
            {"field": field, "reason": str(err["msg"]), "type": etype}
        )
    return out
