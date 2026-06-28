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

from pydantic import BaseModel, ConfigDict, Field, ValidationError

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


class RingSpec(BaseModel):
    """Versioned envelope. archetype is the v1 discriminator (solitaire only).

    v1 uses a single model + Literal discriminator; the true discriminated
    union (oneOf) is deferred to RNG-16 when more archetypes land.
    """

    model_config = ConfigDict(extra="forbid")

    version: Literal["1.0"] = "1.0"
    archetype: Literal["solitaire"] = "solitaire"
    shank: Shank
    setting: Setting
    stones: Stones
    motifs: list[Motif] = Field(default_factory=list)
    confidence: FieldConfidence | None = None


def validate_spec(data: object) -> RingSpec:
    """Validate arbitrary input into a RingSpec, raising ValidationError."""
    return RingSpec.model_validate(data)


def spec_errors(exc: ValidationError) -> list[dict]:
    """Flatten a ValidationError into JSON-serializable field-level errors.

    Each entry is {"field", "reason", "type"} where `field` is the dotted loc
    path ("" for a top-level/body error). Used by RNG-15 to surface 400s.
    """
    out: list[dict] = []
    for err in exc.errors():
        field = ".".join(str(part) for part in err["loc"])
        out.append(
            {"field": field, "reason": str(err["msg"]), "type": str(err["type"])}
        )
    return out
