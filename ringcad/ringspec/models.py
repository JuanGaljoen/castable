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

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, ValidationError, model_validator
from pydantic_core import PydanticCustomError
from pydantic_core import ValidationError as CoreValidationError

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
    8th shaping param); thickness is governed by `SHANK_THICKNESS_TAPER`.

    `outer_profile`/`inner_profile` are the cross-section family (RNG-25): two
    independent axes, not one enum of trade names, because the trade itself
    treats them independently (docs/research/shank-cross-section-profiles.md).
    Both default to `domed`, i.e. "court" -- today's `Ellipse` section -- so
    every spec written before RNG-25 renders identically. See
    `ringcad.ringspec.sections` for what each value means geometrically.
    """

    model_config = ConfigDict(extra="forbid")

    inner_diameter: float = Field(gt=0, le=40)
    band_width: float = Field(gt=0, le=12)
    band_thickness: float = Field(gt=0, le=8)
    shank_taper: float = Field(default=SHANK_WIDTH_TAPER, ge=1.0, le=3.0)
    outer_profile: Literal["domed", "flat", "knife_edge"] = "domed"
    inner_profile: Literal["domed", "flat"] = "domed"


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


class Trilogy(BaseModel):
    """Side-stone group flanking the centre stone (RNG-10)."""

    model_config = ConfigDict(extra="forbid")

    side_stone_diameter: float = Field(default=2.5, ge=0.9, le=6.0)
    side_stone_height: float = Field(default=1.8, ge=0.8, le=4.0)
    side_stone_gap: float = Field(default=0.6, ge=0.3, le=2.0)


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


class RingSpec(BaseModel):
    """The versioned contract (RNG-24): one model, features as optional groups.

    `halo`/`trilogy`/`side_stone` are independently optional — a ring is a base
    (shank/setting/stones) plus whichever features are present, not a choice of
    exactly one archetype. This is CP1 (contract + migration): the schema
    allows any subset, but `validate_castability`'s temporary
    `multi_feature_unvalidated` gate still rejects more than one present until
    CP2 lands real cross-feature checks (docs/adr, specs/RNG-24.md).
    """

    model_config = ConfigDict(extra="forbid")

    version: Literal["1.0"] = "1.0"
    shank: Shank
    setting: Setting
    stones: Stones
    halo: Halo | None = None
    trilogy: Trilogy | None = None
    side_stone: SideStone | None = None
    motifs: list[Motif] = Field(default_factory=list)
    confidence: FieldConfidence | None = None

    @property
    def archetype(self) -> str:
        """Derived, back-compat convenience — NOT a stored discriminator.

        Returns the single active feature's name, or "solitaire" when none is
        set. Meaningful only while at most one feature is present (CP1's own
        gate guarantees that); CP2 gives genuine multi-feature specs their own
        label or drops this property, since "the archetype" stops being a
        well-defined question once more than one feature can coexist.
        """
        if self.halo is not None:
            return "halo"
        if self.trilogy is not None:
            return "trilogy"
        if self.side_stone is not None:
            return "side_stone"
        return "solitaire"


# --- Back-compat constructors -------------------------------------------
# RNG-9/10/11/14 built one class per archetype; RNG-24 retires that union, but
# a large existing test surface (and no production code) constructs these as
# plain factories -- `HaloSpec(shank=..., setting=..., stones=..., halo=...)`.
# Keeping the call shape and returning a RingSpec avoids rewriting every test
# that only ever used these as convenience constructors, while the type itself
# is genuinely unified: `isinstance(spec, HaloSpec)` no longer means anything
# (HaloSpec is a function now), which is the honest signal that the union is
# gone rather than merely renamed.
def SolitaireSpec(**kwargs) -> RingSpec:
    return RingSpec(**kwargs)


def HaloSpec(*, halo: Halo | None = None, **kwargs) -> RingSpec:
    return RingSpec(halo=halo if halo is not None else Halo(), **kwargs)


def TrilogySpec(*, trilogy: Trilogy | None = None, **kwargs) -> RingSpec:
    return RingSpec(trilogy=trilogy if trilogy is not None else Trilogy(), **kwargs)


def SideStoneSpec(*, side_stone: SideStone | None = None, **kwargs) -> RingSpec:
    return RingSpec(
        side_stone=side_stone if side_stone is not None else SideStone(), **kwargs
    )


# The legacy discriminator's known values -> which group it names (None for
# solitaire, which names no group at all).
_LEGACY_ARCHETYPE_GROUP = {
    "solitaire": None,
    "halo": "halo",
    "trilogy": "trilogy",
    "side_stone": "side_stone",
}
_FEATURE_GROUPS = ("halo", "trilogy", "side_stone")


def _tag_error(value: object) -> CoreValidationError:
    err = PydanticCustomError(
        "union_tag_invalid",
        f"Input tag {value!r} found using 'archetype' does not match any of "
        f"the expected tags: {sorted(_LEGACY_ARCHETYPE_GROUP)}",
    )
    return CoreValidationError.from_exception_data(
        "RingSpec", [{"type": err, "loc": ("archetype",), "input": value}]
    )


def _conflict_error(field: str, archetype: str) -> CoreValidationError:
    err = PydanticCustomError(
        "archetype_group_conflict",
        f"archetype {archetype!r} does not use the {field!r} group, but it "
        "was present in the request",
    )
    return CoreValidationError.from_exception_data(
        "RingSpec", [{"type": err, "loc": (field,), "input": None}]
    )


def _missing_group_error(field: str, archetype: str) -> CoreValidationError:
    err = PydanticCustomError(
        "missing", f"archetype {archetype!r} requires the {field!r} group"
    )
    return CoreValidationError.from_exception_data(
        "RingSpec", [{"type": err, "loc": (field,), "input": None}]
    )


def validate_spec(data: object) -> RingSpec:
    """Validate input into a `RingSpec`, raising on failure.

    A legacy `archetype` tag (RNG-9..11) is translated at this edge rather
    than carried into the model: it must name a known archetype, and the
    group it names must be present while every other feature group must be
    absent — preserving the exact back-compat behaviour the discriminated
    union used to enforce structurally. An archetype-less body validates
    directly; any subset of feature groups is legal there (RNG-24).
    """
    if isinstance(data, dict) and "archetype" in data:
        archetype = data["archetype"]
        if archetype not in _LEGACY_ARCHETYPE_GROUP:
            raise _tag_error(archetype)
        expected = _LEGACY_ARCHETYPE_GROUP[archetype]
        for group in _FEATURE_GROUPS:
            # A dumped RingSpec (coherence.make_coherent's `working`, e.g.)
            # always carries all three feature keys, `None` when absent — so
            # "present" means a non-None value, not mere key membership.
            present = data.get(group) is not None
            if group == expected and not present:
                raise _missing_group_error(group, archetype)
            if group != expected and present:
                raise _conflict_error(group, archetype)
        data = {k: v for k, v in data.items() if k != "archetype"}
    return RingSpec.model_validate(data)


def spec_errors(exc: ValidationError) -> list[dict]:
    """Flatten a ValidationError into JSON-serializable field-level errors.

    Each entry is {"field", "reason", "type"}. A None/empty body names ""
    ("" == top-level); every other error's field is its dotted loc path —
    RingSpec is a plain model now, so loc never carries a leading union tag
    to strip (RNG-24).
    """
    out: list[dict] = []
    for err in exc.errors():
        loc = err["loc"]
        field = "" if not loc else ".".join(str(part) for part in loc)
        out.append(
            {"field": field, "reason": str(err["msg"]), "type": str(err["type"])}
        )
    return out
