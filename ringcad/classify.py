"""Claude vision: ring photo -> estimates -> a castable RingSpec.

`classify_ring` never raises; any failure is logged and returned as ok=False.
"""
from __future__ import annotations

import base64
import logging
import math
import os
from dataclasses import dataclass, field
from typing import get_args

import anthropic
from pydantic import BaseModel, ValidationError

from ringcad.ringspec.cuts import profile_for
from ringcad.ringspec import (
    Adjustment,
    Halo,
    Shank,
    SideStone,
    Stones,
    Trilogy,
    is_castable,
    make_coherent,
    validate_spec,
)

logger = logging.getLogger(__name__)

# Bounds for the estimable dimensions. Finger size is never estimated.
CLAMP_BOUNDS = {
    "band_width": (1.6, 6.0),
    "band_thickness": (0.8, 4.0),
    "stone_diameter": (2.0, 10.0),
    "stone_height": (2.0, 6.0),
    "setting_height": (3.0, 8.0),
}

# A photo has no scale, so finger size is never guessed: it stays at this
# default and the user sets it.
DEFAULT_INNER_DIAMETER = 16.5  # ~US6

# Values must match the form inputs' step, or the browser silently blocks
# Generate.
DIMENSION_STEP = 0.1
# Ratios need a finer grid: at 0.1, cushion's 1.02 would become 1.00.
RATIO_STEP = 0.01
_FIELD_STEPS = {"length_ratio": RATIO_STEP}
_DIMENSION_GROUPS = ("shank", "setting", "stones", "halo", "trilogy", "side_stone")

_SHARED_DEFAULTS = {
    "band_width": 2.2,
    "band_thickness": 1.9,
    "stone_diameter": 6.5,
    "stone_height": 4.0,
    "setting_height": 6.0,
    "prong_count": 6,
}

# Buildable features -> (spec group key, model). Field bounds are read off the
# model, so a new feature needs no clamp table here.
_FEATURE_GROUPS = {
    "halo": ("halo", Halo),
    "trilogy": ("trilogy", Trilogy),
    "side_stone": ("side_stone", SideStone),
}
SUPPORTED_FEATURES = ("halo", "trilogy", "side_stone")
# Still read by probes/fidelity_probe.py.
SUPPORTED_ARCHETYPES = ("solitaire",) + SUPPORTED_FEATURES

# Read off the schema so they can't drift from it (docs/adr/0002).
_MAX_LENGTH_RATIO = next(
    (m.le for m in Stones.model_fields["length_ratio"].metadata
     if getattr(m, "le", None) is not None),
    2.5,
)

_BUILDABLE_SHAPES = frozenset(
    get_args(Stones.model_fields["shape"].annotation)
)

_BUILDABLE_OUTER_PROFILES = frozenset(
    get_args(Shank.model_fields["outer_profile"].annotation)
)
_BUILDABLE_INNER_PROFILES = frozenset(
    get_args(Shank.model_fields["inner_profile"].annotation)
)

DEFAULT_MODEL = "claude-haiku-4-5"
DEFAULT_NOTE = "Estimates are rough; verify before generating."

_SYSTEM = (
    "You are a jewelry classifier for engagement rings. Given a photo, "
    "identify the ring and estimate its dimensions in millimetres. Set "
    "`style` to a DETAILED description of the ring in the photo, a sentence "
    "or two, in the words a jeweller would use: the centre stone's cut and "
    "rough size, how it is set, any halo or shoulder stones and how THOSE "
    "are set, the band, and the metal colour (e.g. 'Round brilliant centre "
    "of about 6.5mm in a six-prong head, encircled by a full halo of round "
    "accents, with pave-set diamonds down both shoulders of a white metal "
    "band'). This description is shown to the user to confirm we looked at "
    "the right ring, so describe what is actually visible rather than "
    "naming a style category. Real rings often "
    "combine more than one feature at once -- set `features` to EVERY one of "
    "these three you actually see, in any combination (an empty list means a "
    "plain centre stone with no extra features): 'halo' (a ring of small "
    "accents encircling the centre stone), 'trilogy' (two flanking side "
    "stones beside the centre, each in its own setting), 'side_stone' (a "
    "channel row of small accents set INTO the band down each shoulder, "
    "flush with the surface, not raised or in individual settings). A ring "
    "can have a centre stone with a halo AND side-stone shoulders at once -- "
    "list both. Estimate the dimensions of EVERY feature group you listed "
    "(halo_*, side_stone_* for trilogy, accent_* for side_stone). "
    "EVERY field is required: fill in a number for every dimension, and use "
    "0 for any dimension you cannot estimate or that does not apply -- a "
    "feature you did NOT list in `features` always gets 0 for every one of "
    "its own dimensions. Set "
    "`stone_shape` to the centre stone's CUT, one of exactly these six: "
    "'round' (a circle), 'oval' (a smooth ellipse, no corners or points), "
    "'cushion' (a square or slightly oblong outline with ROUNDED corners and "
    "sides that bow outward), 'emerald' (a rectangle with STRAIGHT sides and "
    "small angled cut-off corners, showing a large flat table and concentric "
    "rectangular steps rather than sparkling triangular facets), 'pear' (a "
    "teardrop: one round end tapering to a single sharp POINT), or 'marquise' "
    "(a narrow boat or eye shape with sharp POINTS at BOTH ends). Answer "
    "'round' for any other cut (princess, trillion, heart, asscher, radiant) "
    "and for anything you are unsure of. Set `stone_length_ratio` to "
    "the stone's length divided by its width as it appears in the photo (1.0 "
    "for a round stone, about 1.5 for a typical oval, 2.0 for a marquise); "
    "this is a ratio you can see directly, unlike absolute millimetres, so "
    "measure it from the image rather than recalling a typical value for the "
    "cut -- use 0 only if the stone is too obscured to measure. Set "
    "`outer_profile` (the OUTSIDE of the band, facing away from the finger) "
    "to one of: 'domed' (rounded, the ordinary curved band), 'flat' (a flat "
    "top with sharp edges), or 'knife_edge' (rises to a visible ridge or "
    "peak down the centre). Set `inner_profile` (the INSIDE of the band, "
    "against the finger) to one of: 'domed' (rounded/comfort-fit interior, "
    "usually not visible in a photo -- answer 'domed' unless you can "
    "actually see the inside) or 'flat'. These are independent: a band can "
    "be domed outside with a flat inside, or any other combination. Answer "
    "'domed' for both if unsure or if the profile is not clearly visible. "
    "Give a per-field `confidence` in [0,1] for each shared dimension (0 when you "
    "did not estimate it). If the image does not clearly show a single ring, "
    "set ring_detected to false and set every dimension to 0. Never "
    "guess finger size or inner diameter -- there is no field for it. All "
    "millimetre estimates are rough approximations."
)
_USER = (
    "Classify this ring: list every feature you see, describe the style, and "
    "estimate its dimensions in millimetres. If it is not a clear photo of a "
    "single ring, set ring_detected to false."
)


class RingConfidence(BaseModel):
    """Per-field confidence in [0,1]; 0 means not estimated. Every field is
    required (docs/adr/0004)."""

    band_width: float
    band_thickness: float
    stone_diameter: float
    stone_height: float
    setting_height: float
    prong_count: float


class RingClassification(BaseModel):
    """The structured output Claude fills in.

    Every field is required, with 0 meaning "not estimated": optional fields
    make the real API hang or reject the schema (docs/adr/0004). There is
    deliberately no finger-size field.
    """

    ring_detected: bool
    style: str
    prong_count: int
    shank_taper: str
    features: list[str]
    band_width: float
    band_thickness: float
    stone_diameter: float
    stone_height: float
    setting_height: float
    # Plain str, not Literal (docs/adr/0004); validated in code.
    outer_profile: str
    inner_profile: str
    # Plain str, not Literal (docs/adr/0004); an unknown cut becomes round.
    stone_shape: str
    stone_length_ratio: float
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
    """What vision saw. `features` is any subset of SUPPORTED_FEATURES."""

    ok: bool
    ring_detected: bool
    style: str
    shank_taper: str
    note: str
    prong_count: int
    features: list[str]
    estimates: dict[str, float]
    group_estimates: dict = field(default_factory=dict)
    confidence: dict = field(default_factory=dict)
    stone_shape: str = "round"
    stone_length_ratio: float = 1.0
    outer_profile: str = "domed"
    inner_profile: str = "domed"

    def to_spec(self) -> dict | None:
        """A castable RingSpec, or None when no ring was detected."""
        return self._coherent_spec()[0]

    def _coherent_spec(self) -> tuple[dict | None, list[Adjustment]]:
        """Build a spec and repair it against the casting gate, since fields
        that are each valid can still be impossible together.

        Falls back step by step: detected features -> no features -> pure
        defaults, which are always castable (docs/adr/0009).
        """
        if not self.ring_detected:
            return None, []
        for features, group_estimates in (
            (self.features, self.group_estimates),
            ([], {}),
        ):
            label = "+".join(features) if features else "solitaire"
            try:
                spec = self._assemble(features, group_estimates)
                validate_spec(spec)
            except ValidationError:
                logger.error(
                    "assembled %s spec failed validation; trying next "
                    "fallback", label, exc_info=True,
                )
                continue
            coherent, adjustments = make_coherent(spec, self.confidence)
            if is_castable(validate_spec(coherent)):
                stepped = _settle_on_step_grid(coherent)
                if stepped is not None:
                    return stepped, adjustments
                logger.error(
                    "%s spec did not settle on the step grid castably; "
                    "trying next fallback", label,
                )
                continue
            logger.error(
                "%s spec still uncastable after repair; trying next "
                "fallback", label,
            )
        return self._assemble([], {}, estimates={}), []

    def _assemble(self, features: list[str], groups: dict,
                  estimates: dict | None = None) -> dict:
        """Assemble a spec dict. Passing `estimates={}` gives pure defaults with
        a round stone, the last-resort fallback."""
        est = self.estimates if estimates is None else estimates
        spec = {
            "version": "1.0",
            "shank": {
                "inner_diameter": DEFAULT_INNER_DIAMETER,
                "band_width": est.get("band_width", _SHARED_DEFAULTS["band_width"]),
                "band_thickness": est.get(
                    "band_thickness", _SHARED_DEFAULTS["band_thickness"]),
                **({} if estimates is not None else
                   _shank_profile(self.outer_profile, self.inner_profile)),
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
                **({} if estimates is not None else
                   _stone_shape(self.stone_shape, self.stone_length_ratio)),
            },
        }
        if self.confidence:
            spec["confidence"] = dict(self.confidence)
        for name in features:
            if name not in _FEATURE_GROUPS:
                continue
            group_key = _FEATURE_GROUPS[name][0]
            # An empty dict lets the schema fill in group defaults.
            spec[group_key] = dict(groups.get(group_key, {}))
        return spec

    def to_json(self) -> dict:
        spec, adjustments = self._coherent_spec()
        return {
            "ring_detected": self.ring_detected,
            "detected_style": self.style,
            "note": self.note,
            "spec": spec,
            # Fields the repair changed, so the form can flag them.
            "adjustments": [a.model_dump() for a in adjustments],
        }


def _settle_on_step_grid(coherent: dict) -> dict | None:
    """Round onto the form's step grid without breaking castability: try
    nearest, then up, then down. None if none of them stays castable."""
    for direction in ("nearest", "ceil", "floor"):
        stepped = _round_to_step(coherent, direction)
        if is_castable(validate_spec(stepped)):
            return stepped
    return None


_STEP_ROUNDERS = {"nearest": round, "ceil": math.ceil, "floor": math.floor}


def _to_step(value: float, step: float, step_round) -> float:
    """Snap `value` onto the `step` grid, without float noise (1.9000000001)."""
    return round(step_round(value / step) * step,
                 max(0, -math.floor(math.log10(step) + 1e-9)))


def _round_to_step(spec: dict, direction: str = "nearest") -> dict:
    """Round every float in the dimension groups to its form step. Returns a
    new dict."""
    step_round = _STEP_ROUNDERS[direction]
    out = dict(spec)
    for group_key in _DIMENSION_GROUPS:
        group = spec.get(group_key)
        if not isinstance(group, dict):
            continue
        out[group_key] = {
            k: _to_step(v, _FIELD_STEPS.get(k, DIMENSION_STEP), step_round)
            if isinstance(v, float) else v
            for k, v in group.items()
        }
    return out


def _shank_profile(outer: str, inner: str) -> dict:
    """Vision's band profile -> spec fields. Anything unknown becomes `domed`
    rather than failing the whole classification."""
    outer_name = (outer or "").strip().lower()
    inner_name = (inner or "").strip().lower()
    return {
        "outer_profile": (
            outer_name if outer_name in _BUILDABLE_OUTER_PROFILES else "domed"
        ),
        "inner_profile": (
            inner_name if inner_name in _BUILDABLE_INNER_PROFILES else "domed"
        ),
    }


def _stone_shape(shape: str, ratio: float) -> dict:
    """Vision's stone cut and ratio -> spec fields.

    An unbuildable cut (princess, heart, ...) becomes round rather than failing.
    A ratio of 0 (not estimated) takes the cut's usual default; an out-of-range
    ratio is clamped to the nearest value the cut allows. An oval at 1.0 is a
    circle, so it's recorded as round.
    """
    name = (shape or "").strip().lower()
    try:
        value = float(ratio)
    except (TypeError, ValueError):
        value = 0.0
    if name not in _BUILDABLE_SHAPES:
        return {"shape": "round", "length_ratio": 1.0}
    if name == "round":
        return {"shape": "round", "length_ratio": 1.0}
    profile = profile_for(name)
    if value <= 0:                      # not estimated
        value = profile.default_ratio
    value = max(profile.min_ratio, min(profile.max_ratio, value))
    if name == "oval" and value <= 1.0:
        return {"shape": "round", "length_ratio": 1.0}
    return {"shape": name, "length_ratio": value}


def _model() -> str:
    return os.environ.get("CLASSIFY_MODEL", DEFAULT_MODEL)


def _clamp(key: str, value) -> float:
    lo, hi = CLAMP_BOUNDS[key]
    return max(lo, min(hi, float(value)))


def _snap_prong(n: int) -> int:
    return 4 if abs(n - 4) <= abs(n - 6) else 6


def _field_bounds(model_cls, name: str) -> tuple[float | None, float | None]:
    """(ge, le) from a Pydantic field's constraints."""
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


def _group_estimates(features: list[str], data: "RingClassification") -> dict:
    """Clamp each detected feature's dimensions to the schema bounds. Fields
    left at 0 are omitted so the schema default applies."""
    out: dict = {}
    for name in features:
        if name not in _FEATURE_GROUPS:
            continue
        group_key, model_cls = _FEATURE_GROUPS[name]
        group_out: dict = {}
        for fname, fld in model_cls.model_fields.items():
            raw = getattr(data, fname, 0.0)
            if not raw or raw <= 0:  # 0 = not estimated
                continue
            lo, hi = _field_bounds(model_cls, fname)
            if fld.annotation is int:
                group_out[fname] = int(_clamp_bounds(lo, hi, round(float(raw))))
            else:
                group_out[fname] = _clamp_bounds(lo, hi, float(raw))
        out[group_key] = group_out
    return out


def _confidence(data: "RingConfidence | None") -> dict:
    """RingConfidence -> {field: value in [0,1]}, dropping unset entries."""
    if data is None:
        return {}
    out: dict = {}
    for name in RingConfidence.model_fields:
        val = getattr(data, name, 0.0)
        if val and val > 0:
            out[name] = max(0.0, min(1.0, float(val)))
    return out


def _valid_features(raw: list[str]) -> list[str]:
    """Keep only known features, deduplicated; unknown ones are dropped."""
    out: list[str] = []
    for name in raw:
        key = (name or "").strip().lower()
        if key in SUPPORTED_FEATURES and key not in out:
            out.append(key)
    return out


def _note(model_note: str) -> str:
    """The caveat shown with the estimates."""
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
            if getattr(data, key) and getattr(data, key) > 0  # 0 = not estimated
        }
        estimates["prong_count"] = _snap_prong(data.prong_count)
        features = _valid_features(data.features)
        return ClassifyResult(
            ok=True,
            ring_detected=True,
            style=data.style,
            shank_taper=data.shank_taper,
            note=_note(data.note),
            prong_count=_snap_prong(data.prong_count),
            features=features,
            estimates=estimates,
            group_estimates=_group_estimates(features, data),
            confidence=_confidence(data.confidence),
            stone_shape=data.stone_shape,
            stone_length_ratio=data.stone_length_ratio,
            outer_profile=data.outer_profile,
            inner_profile=data.inner_profile,
        )
    except Exception:
        logger.error("classify_ring failed", exc_info=True)
        return _empty(ok=False, ring_detected=False, note="")
