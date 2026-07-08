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
)

SPEC_VERSION = "1.0"

# Generous physical caps — structural sanity only, NOT casting floors. The
# lower casting floors (min wall / min tip) are enforced in castability.py.


class Shank(BaseModel):
    """Band geometry. shank_taper is the SCAD 8th shaping param (default 1.7)."""

    model_config = ConfigDict(extra="forbid")

    inner_diameter: float = Field(gt=0, le=40)
    band_width: float = Field(gt=0, le=12)
    band_thickness: float = Field(gt=0, le=8)
    shank_taper: float = Field(default=1.7, ge=1.0, le=3.0)


class Setting(BaseModel):
    """Prong/gallery group. prong_count is a strict 4-or-6 literal."""

    model_config = ConfigDict(extra="forbid")

    prong_count: Literal[4, 6]
    setting_height: float = Field(gt=0, le=20)


class Stones(BaseModel):
    """Centre-stone sizing for the seat module."""

    model_config = ConfigDict(extra="forbid")

    stone_diameter: float = Field(gt=0, le=24)
    stone_height: float = Field(gt=0, le=12)


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
    """Accent-stone ring encircling the centre stone (RNG-9)."""

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


ARCHETYPE_TAGS = {"solitaire", "halo", "trilogy"}

# The versioned contract is a discriminated (tagged) union over `archetype`.
# `RingSpec` is an Annotated alias — a type hint, NOT an instantiable class;
# construct a concrete member (SolitaireSpec/HaloSpec/TrilogySpec) or route
# dict/JSON input through validate_spec (which uses the adapter below).
RingSpec = Annotated[
    Union[SolitaireSpec, HaloSpec, TrilogySpec], Field(discriminator="archetype")
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
