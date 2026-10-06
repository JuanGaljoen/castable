"""RingSpec v1 — the versioned, typed contract between vision and geometry.

The schema checks structure only (types, ranges, allowed values). Casting
floors live in `castability.py`, so a well-formed but uncastable spec can be
built and then flagged: vision can produce those.
"""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, ValidationError, model_validator
from pydantic_core import PydanticCustomError
from pydantic_core import ValidationError as CoreValidationError

SPEC_VERSION = "1.0"

# The band widens toward the head; thickness stays near-constant so the ring
# feels even on the finger. Defined here, not in geometry, because both the
# builder and castability.py need them, and ringspec can't import geometry
# (docs/adr/0002).
SHANK_WIDTH_TAPER = 1.35
SHANK_THICKNESS_TAPER = 1.15
FLAT_TAPER = 1.0

# --- Channel setting ---------------------------------------------------------
# Shared by the gate and the builder. Stones sit in a groove cut into the band;
# cutting each stone at full width bites into the walls and forms the bearings.
GIRDLE_PENETRATION = 0.2  # how far each girdle edge tucks into its wall
GIRDLE_RECESS = 0.2       # how far the girdle sits below the band's surface
PAVILION_FRACTION = 0.65  # share of a stone's height below its girdle


def channel_groove_depth(accent_stone_height: float) -> float:
    """Radial depth of the channel trench, measured in from the band's outer
    surface: the stone's pavilion plus the girdle's recess below the surface."""
    return PAVILION_FRACTION * accent_stone_height + GIRDLE_RECESS


# --- Halo plate --------------------------------------------------------------
# Metal beyond the outermost seat. 0.5mm is the trade figure for a bright-cut
# edge (ganoksin.com, single-row pave guide). An overhang, not a wall, so it may
# sit below MIN_WALL.
HALO_PLATE_RIM = 0.5
# How far the plate reaches inside the centre girdle, embedding the centre claws
# so they carry the halo. Wider than the claw radius (0.5) for a solid weld.
HALO_PLATE_INNER_BITE = 0.7
# A seat is a tapered bearing: its bottom radius as a fraction of the stone's.
HALO_WELL_BACK_RATIO = 0.5
HALO_MIN_SEAT_DEPTH = 0.2


def halo_seat_depth(
    accent_stone_height: float, available: float, min_wall: float
) -> float:
    """Seat depth: the stone's pavilion, clamped to the metal available, so a
    tall accent on a low setting can't push the halo through the band."""
    return max(HALO_MIN_SEAT_DEPTH,
               min(PAVILION_FRACTION * accent_stone_height, available - min_wall))


def halo_plate_thickness(accent_stone_height: float, min_wall: float) -> float:
    """Plate thickness: the seat's own depth plus a floor beneath it."""
    return PAVILION_FRACTION * accent_stone_height + min_wall


def halo_min_arc(
    accent_stone_diameter: float, min_wall: float, min_prong_tip: float
) -> float:
    """Arc each accent needs so the metal BETWEEN adjacent seats survives.

    Measured where the tapered bores are narrowest, not at the girdle: the metal
    between two seats is a V-shaped ridge, and its thin top edge is not the
    wall. That gives `pitch >= min_wall + 2 * back_r`, and never less than the
    stone's own diameter (stones must not overlap).
    """
    back_r = accent_stone_diameter / 2 * HALO_WELL_BACK_RATIO
    return max(accent_stone_diameter, min_wall + 2 * back_r)


def channel_band_width(accent_stone_diameter: float, min_wall: float) -> float:
    """Band width a channel needs: the stone plus a wall each side."""
    return accent_stone_diameter + 2 * min_wall


class Shank(BaseModel):
    """Band geometry. `shank_taper` is the width flare toward the head.

    The outer and inner profiles are independent because the trade treats them
    that way (docs/research/shank-cross-section-profiles.md). Both default to
    `domed`, a classic court band.
    """

    model_config = ConfigDict(extra="forbid")

    inner_diameter: float = Field(gt=0, le=40)
    band_width: float = Field(gt=0, le=12)
    band_thickness: float = Field(gt=0, le=8)
    shank_taper: float = Field(default=SHANK_WIDTH_TAPER, ge=1.0, le=3.0)
    outer_profile: Literal["domed", "flat", "knife_edge"] = "domed"
    inner_profile: Literal["domed", "flat"] = "domed"


class Setting(BaseModel):
    """Prong count and setting height."""

    model_config = ConfigDict(extra="forbid")

    prong_count: Literal[4, 6]
    setting_height: float = Field(gt=0, le=20)


class Stones(BaseModel):
    """Centre stone size and shape.

    `stone_diameter` is the SHORT axis; the long axis is
    `stone_diameter * length_ratio`. A ratio, not a length, because a ratio is
    what a photo shows. Defaults mean a round stone.
    """

    model_config = ConfigDict(extra="forbid")

    stone_diameter: float = Field(gt=0, le=24)
    stone_height: float = Field(gt=0, le=12)
    shape: Literal["round", "oval", "cushion", "emerald", "pear",
                   "marquise"] = "round"
    length_ratio: float = Field(default=1.0, ge=1.0, le=2.5)

    @model_validator(mode="after")
    def _ratio_within_the_cuts_band(self):
        """Keep `length_ratio` inside the cut's own band.

        Below it, use the cut's conventional default (a marquise at 1.0 is a
        circle, not a marquise). Above it, clamp to the ceiling (a cushion at
        2.38 is not a cushion). Corrected rather than rejected: these are trade
        conventions, not standards.
        """
        from .cuts import profile_for
        profile = profile_for(self.shape)
        if self.length_ratio < profile.min_ratio:
            object.__setattr__(self, "length_ratio", profile.default_ratio)
        elif self.length_ratio > profile.max_ratio:
            object.__setattr__(self, "length_ratio", profile.max_ratio)
        return self


class Motif(BaseModel):
    """Decorative element placeholder."""

    model_config = ConfigDict(extra="forbid")

    kind: str
    position: float | None = None


class FieldConfidence(BaseModel):
    """Per-field vision confidence (0..1), filled by the photo classifier; None
    where vision gave no estimate."""

    model_config = ConfigDict(extra="forbid")

    inner_diameter: float | None = Field(default=None, ge=0, le=1)
    band_width: float | None = Field(default=None, ge=0, le=1)
    band_thickness: float | None = Field(default=None, ge=0, le=1)
    stone_diameter: float | None = Field(default=None, ge=0, le=1)
    stone_height: float | None = Field(default=None, ge=0, le=1)
    prong_count: float | None = Field(default=None, ge=0, le=1)
    setting_height: float | None = Field(default=None, ge=0, le=1)


class Halo(BaseModel):
    """Accent stones around the centre stone. Whether they fit is checked by
    the castability gate, not here."""

    model_config = ConfigDict(extra="forbid")

    halo_stone_diameter: float = Field(default=1.3, ge=0.9, le=2.5)
    halo_stone_count: int = Field(default=14, ge=8, le=24)
    halo_gap: float = Field(default=0.5, ge=0.3, le=1.5)
    halo_stone_height: float = Field(default=1.2, ge=0.8, le=3.0)


class Trilogy(BaseModel):
    """Side-stone group flanking the centre stone."""

    model_config = ConfigDict(extra="forbid")

    side_stone_diameter: float = Field(default=2.5, ge=0.9, le=6.0)
    side_stone_height: float = Field(default=1.8, ge=0.8, le=4.0)
    side_stone_gap: float = Field(default=0.6, ge=0.3, le=2.0)


class SideStone(BaseModel):
    """Channel-set accent row down each shoulder. Only channel retention
    exists so far; "pave" is rejected rather than built wrong."""

    model_config = ConfigDict(extra="forbid")

    accent_stone_diameter: float = Field(default=1.5, ge=0.9, le=2.5)
    accent_stone_height: float = Field(default=1.2, ge=0.8, le=3.0)
    accent_count_per_side: int = Field(default=3, ge=1, le=8)
    accent_gap: float = Field(default=0.3, ge=0.2, le=1.0)
    retention: Literal["channel"] = "channel"


class RingSpec(BaseModel):
    """A ring: a base (shank, setting, stones) plus any mix of optional
    features. Whether the features fit together is the gate's job."""

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
        """The first feature present, or "solitaire". A label only: never
        write it back into a spec (docs/adr/0013)."""
        if self.halo is not None:
            return "halo"
        if self.trilogy is not None:
            return "trilogy"
        if self.side_stone is not None:
            return "side_stone"
        return "solitaire"


def effective_thickness_taper(spec: RingSpec) -> float:
    """Thickness taper: none for a side-stone band (a channel needs a constant
    radius), otherwise the normal head taper. Shared by gate and builder."""
    return FLAT_TAPER if spec.side_stone is not None else SHANK_THICKNESS_TAPER


# --- Back-compat constructors -------------------------------------------
# Convenience factories kept for tests; each returns a plain RingSpec.
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


# Legacy `archetype` tag -> the feature group it names.
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

    A legacy `archetype` tag is still accepted: its group must be present and
    every other feature group absent. Without the tag, any mix is allowed.
    """
    if isinstance(data, dict) and "archetype" in data:
        archetype = data["archetype"]
        if archetype not in _LEGACY_ARCHETYPE_GROUP:
            raise _tag_error(archetype)
        expected = _LEGACY_ARCHETYPE_GROUP[archetype]
        for group in _FEATURE_GROUPS:
            # A dumped spec carries every key, None when absent.
            present = data.get(group) is not None
            if group == expected and not present:
                raise _missing_group_error(group, archetype)
            if group != expected and present:
                raise _conflict_error(group, archetype)
        data = {k: v for k, v in data.items() if k != "archetype"}
    return RingSpec.model_validate(data)


def spec_errors(exc: ValidationError) -> list[dict]:
    """Flatten a ValidationError into {"field", "reason", "type"} entries,
    where field is the dotted path ("" for the top level)."""
    out: list[dict] = []
    for err in exc.errors():
        loc = err["loc"]
        field = "" if not loc else ".".join(str(part) for part in loc)
        out.append(
            {"field": field, "reason": str(err["msg"]), "type": str(err["type"])}
        )
    return out
