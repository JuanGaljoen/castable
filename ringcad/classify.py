"""Claude vision ring classifier (RNG-6).

Wraps a single Anthropic vision call behind `classify_ring`, which NEVER raises:
any SDK/parse/timeout failure is logged and surfaced as a result with ok=False.
The API key is read via env only; it never reaches a result body or a log line.
"""
from __future__ import annotations

import base64
import logging
import os
from dataclasses import dataclass, field

import anthropic
from pydantic import BaseModel, ValidationError

from ringcad.ringspec import (
    Halo,
    SideStone,
    Trilogy,
    validate_spec,
)

logger = logging.getLogger(__name__)

# Casting-aware clamp bounds for the five estimable dimensions. inner_diameter
# (finger size) is deliberately absent -- it is never guessed from a photo.
CLAMP_BOUNDS = {
    "band_width": (1.6, 6.0),
    "band_thickness": (0.8, 4.0),
    "stone_diameter": (2.0, 10.0),
    "stone_height": (2.0, 6.0),
    "setting_height": (3.0, 8.0),
}

# Shared-dim defaults for fields the photo did not (or must not) estimate. They
# match the form defaults / docs/parameter-ranges.md so an assembled spec is
# always complete and castable. inner_diameter (finger size) is NEVER guessed
# from a photo (RNG-6 rule) -- it stays at this default with confidence None.
DEFAULT_INNER_DIAMETER = 16.5  # ~US6
_SHARED_DEFAULTS = {
    "band_width": 2.2,
    "band_thickness": 1.9,
    "stone_diameter": 6.5,
    "stone_height": 4.0,
    "setting_height": 6.0,
    "prong_count": 6,
}

# RNG-12: which archetypes the module library can build, and each one's group
# key + Pydantic group model (source of truth for the group field bounds). The
# group fields are read off the model, so a new archetype needs no per-field
# clamp table here.
_ARCHETYPE_GROUPS = {
    "halo": ("halo", Halo),
    "trilogy": ("trilogy", Trilogy),
    "side_stone": ("side_stone", SideStone),
}
SUPPORTED_ARCHETYPES = ("solitaire", "halo", "trilogy", "side_stone")

DEFAULT_MODEL = "claude-haiku-4-5"
DEFAULT_NOTE = "Estimates are rough; verify before generating."

_SYSTEM = (
    "You are a jewelry classifier for engagement rings. Given a photo, "
    "identify the ring and estimate its dimensions in millimetres. Set "
    "`style` to a free-text description of what you actually see (e.g. "
    "'cathedral pave halo'). Set `archetype` to the NEAREST of the four "
    "supported buildable styles: solitaire (a single centre stone), halo (a "
    "ring of small accents around the centre), trilogy (one centre plus two "
    "flanking side stones), or side_stone (a channel row of small accents "
    "down each shoulder). Estimate the dimensions of the chosen archetype's "
    "group (halo_*, side_stone_* for trilogy, accent_* for side_stone). "
    "EVERY field is required: fill in a number for every dimension, and use "
    "0 for any dimension you cannot estimate or that does not apply to the "
    "chosen archetype (e.g. the halo_* fields on a solitaire). Give a "
    "per-field `confidence` in [0,1] for each shared dimension (0 when you "
    "did not estimate it). If the image does not clearly show a single ring, "
    "set ring_detected to false and set every dimension to 0. Never "
    "guess finger size or inner diameter -- there is no field for it. All "
    "millimetre estimates are rough approximations."
)
_USER = (
    "Classify this ring: pick the nearest supported archetype, describe the "
    "style you see, and estimate its dimensions in millimetres. If it is not "
    "a clear photo of a single ring, set ring_detected to false."
)


class RingConfidence(BaseModel):
    """Per-field vision confidence in [0,1] for the shared dimensions. Bounds
    are omitted from the schema (structured-output constraint stripping) and
    clamped in code. EVERY field is required (no defaults): strict structured
    output treats a defaulted field as optional, and many optional fields blow
    up server-side compilation (RNG-21). 0.0 means "no confidence".
    inner_diameter is absent -- never guessed."""

    band_width: float
    band_thickness: float
    stone_diameter: float
    stone_height: float
    setting_height: float
    prong_count: float


class RingClassification(BaseModel):
    """Structured output schema for messages.parse. `style` is the free-text
    detected style; `archetype` is the nearest supported buildable style. Only
    the chosen archetype's group dims are read; the rest are ignored. No
    inner_diameter field (never guessed).

    EVERY field is REQUIRED (no defaults). Strict structured output treats a
    field with a default as optional, and a schema with many optional fields
    incurs exponential compilation cost -- the real Messages API then hangs and
    times out (RNG-21, the "17 params with type arrays or anyOf" 400 was the
    same root cause surfacing as a hard reject). The model instead fills every
    field and uses 0 for a dimension it cannot estimate or that does not apply
    to the chosen archetype; parsing treats 0 as "not estimated" and falls back
    to the shared/group default. See tests/test_classify_schema for the guard."""

    ring_detected: bool
    style: str
    archetype: str
    prong_count: int
    shank_taper: str
    features: list[str]
    band_width: float
    band_thickness: float
    stone_diameter: float
    stone_height: float
    setting_height: float
    # Halo group
    halo_stone_diameter: float
    halo_stone_count: float
    halo_gap: float
    halo_stone_height: float
    # Trilogy group
    side_stone_diameter: float
    side_stone_height: float
    side_stone_gap: float
    # Side-stone (channel) group
    accent_stone_diameter: float
    accent_stone_height: float
    accent_count_per_side: float
    accent_gap: float
    confidence: RingConfidence
    note: str


@dataclass(frozen=True)
class ClassifyResult:
    ok: bool
    ring_detected: bool
    style: str
    shank_taper: str
    note: str
    prong_count: int
    features: list[str]
    estimates: dict[str, float]
    archetype: str = "solitaire"
    group_estimates: dict = field(default_factory=dict)
    confidence: dict = field(default_factory=dict)

    def to_spec(self) -> dict | None:
        """Assemble a validated RingSpec (archetype + groups + confidence), or
        None when no ring was detected. Shared dims come from `estimates` over
        `_SHARED_DEFAULTS`; inner_diameter is never estimated. If the assembled
        spec fails schema validation it falls back to a solitaire built from the
        shared dims, preserving never-500."""
        if not self.ring_detected:
            return None
        spec = self._assemble(self.archetype, self.group_estimates)
        try:
            validate_spec(spec)
            return spec
        except ValidationError:
            logger.error("assembled spec failed validation; solitaire fallback",
                         exc_info=True)
            return self._assemble("solitaire", {})

    def _assemble(self, archetype: str, group: dict) -> dict:
        est = self.estimates
        spec = {
            "version": "1.0",
            "archetype": archetype,
            "shank": {
                "inner_diameter": DEFAULT_INNER_DIAMETER,
                "band_width": est.get("band_width", _SHARED_DEFAULTS["band_width"]),
                "band_thickness": est.get(
                    "band_thickness", _SHARED_DEFAULTS["band_thickness"]),
            },
            "setting": {
                "prong_count": est.get(
                    "prong_count", _SHARED_DEFAULTS["prong_count"]),
                "setting_height": est.get(
                    "setting_height", _SHARED_DEFAULTS["setting_height"]),
            },
            "stones": {
                "stone_diameter": est.get(
                    "stone_diameter", _SHARED_DEFAULTS["stone_diameter"]),
                "stone_height": est.get(
                    "stone_height", _SHARED_DEFAULTS["stone_height"]),
            },
        }
        if self.confidence:
            spec["confidence"] = dict(self.confidence)
        if archetype in _ARCHETYPE_GROUPS:
            # Always emit the group key -- an empty dict lets the schema fill
            # every group default (each group field is optional-with-default).
            spec[_ARCHETYPE_GROUPS[archetype][0]] = dict(group)
        return spec

    def to_json(self) -> dict:
        return {
            "ring_detected": self.ring_detected,
            "detected_style": self.style,
            "note": self.note,
            "spec": self.to_spec(),
        }


def _model() -> str:
    return os.environ.get("CLASSIFY_MODEL", DEFAULT_MODEL)


def _clamp(key: str, value) -> float:
    lo, hi = CLAMP_BOUNDS[key]
    return max(lo, min(hi, float(value)))


def _snap_prong(n: int) -> int:
    return 4 if abs(n - 4) <= abs(n - 6) else 6


def _field_bounds(model_cls, name: str) -> tuple[float | None, float | None]:
    """Read (ge, le) from a Pydantic field's constraint metadata -- the single
    source of truth for a group field's range."""
    lo = hi = None
    for meta in model_cls.model_fields[name].metadata:
        if hasattr(meta, "ge"):
            lo = meta.ge
        if hasattr(meta, "le"):
            hi = meta.le
    return lo, hi


def _clamp_bounds(lo, hi, value: float) -> float:
    if lo is not None:
        value = max(lo, value)
    if hi is not None:
        value = min(hi, value)
    return value


def _group_estimates(archetype: str, data: "RingClassification") -> dict:
    """Clamp each group dim the model returned to its RingSpec field bounds;
    int-typed counts are rounded and snapped to int. Fields the model left null
    are omitted so the schema default applies."""
    if archetype not in _ARCHETYPE_GROUPS:
        return {}
    _, model_cls = _ARCHETYPE_GROUPS[archetype]
    out: dict = {}
    for name, fld in model_cls.model_fields.items():
        raw = getattr(data, name, 0.0)
        # 0.0 is the "not estimated" sentinel (dims are strictly positive).
        if not raw or raw <= 0:
            continue
        lo, hi = _field_bounds(model_cls, name)
        if fld.annotation is int:
            out[name] = int(_clamp_bounds(lo, hi, round(float(raw))))
        else:
            out[name] = _clamp_bounds(lo, hi, float(raw))
    return out


def _confidence(data: "RingConfidence | None") -> dict:
    """Flatten a RingConfidence into a {field: value in [0,1]} dict, dropping
    unset entries (0.0 sentinel). inner_diameter is never present (never
    estimated)."""
    if data is None:
        return {}
    out: dict = {}
    for name in RingConfidence.model_fields:
        val = getattr(data, name, 0.0)
        if val and val > 0:
            out[name] = max(0.0, min(1.0, float(val)))
    return out


def _note(archetype: str, style: str, model_note: str) -> str:
    """When the detected free-text style doesn't name the buildable archetype,
    say we fell back to the nearest supported style (RNG-12 decision 1)."""
    label = archetype.replace("_", " ")
    if style and label not in style.lower().replace("_", " "):
        return (
            f"Detected {style} -- building the nearest supported style "
            f"({label}). Verify before generating."
        )
    return model_note or DEFAULT_NOTE


def _empty(ok: bool, ring_detected: bool, note: str) -> ClassifyResult:
    return ClassifyResult(
        ok=ok,
        ring_detected=ring_detected,
        style="",
        shank_taper="",
        note=note,
        prong_count=6,
        features=[],
        estimates={},
    )


def classify_available() -> bool:
    """True iff an API key is configured. Env-only -- builds no client."""
    return bool(os.environ.get("ANTHROPIC_API_KEY"))


def classify_ring(image_bytes: bytes, media_type: str) -> ClassifyResult:
    """Classify a ring photo. Never raises; never leaks the key into the result."""
    try:
        client = anthropic.Anthropic()
        resp = client.with_options(timeout=30.0, max_retries=0).messages.parse(
            model=_model(),
            max_tokens=512,
            system=_SYSTEM,
            messages=[
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image",
                            "source": {
                                "type": "base64",
                                "media_type": media_type,
                                "data": base64.standard_b64encode(
                                    image_bytes
                                ).decode(),
                            },
                        },
                        {"type": "text", "text": _USER},
                    ],
                }
            ],
            output_format=RingClassification,
        )
        data = resp.parsed_output
        if data is None:
            return _empty(ok=False, ring_detected=False, note="")
        if not data.ring_detected:
            return _empty(
                ok=True,
                ring_detected=False,
                note=data.note or "No ring detected in the photo.",
            )
        estimates: dict[str, float] = {
            key: _clamp(key, getattr(data, key))
            for key in CLAMP_BOUNDS
            # 0.0 is the "not estimated" sentinel (dims are strictly positive).
            if getattr(data, key) and getattr(data, key) > 0
        }
        estimates["prong_count"] = _snap_prong(data.prong_count)
        archetype = (
            data.archetype if data.archetype in SUPPORTED_ARCHETYPES
            else "solitaire"
        )
        return ClassifyResult(
            ok=True,
            ring_detected=True,
            style=data.style,
            shank_taper=data.shank_taper,
            note=_note(archetype, data.style, data.note),
            prong_count=_snap_prong(data.prong_count),
            features=list(data.features),
            estimates=estimates,
            archetype=archetype,
            group_estimates=_group_estimates(archetype, data),
            confidence=_confidence(data.confidence),
        )
    except Exception:
        logger.error("classify_ring failed", exc_info=True)
        return _empty(ok=False, ring_detected=False, note="")
