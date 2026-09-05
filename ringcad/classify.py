"""Claude vision ring classifier (RNG-6).

Wraps a single Anthropic vision call behind `classify_ring`, which NEVER raises:
any SDK/parse/timeout failure is logged and surfaced as a result with ok=False.
The API key is read via env only; it never reaches a result body or a log line.
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

# RNG-38: every stepped dimension input in templates/index.html uses step="0.1"
# (counts use step="1", already satisfied since they're int by construction).
# Nothing before this rounded a value to that grid, so the browser's native
# number-input validation silently blocked Generate whenever an estimate --
# or a coherence-repaired value -- wasn't an exact multiple of 0.1.
DIMENSION_STEP = 0.1
# `length_ratio` is a RATIO, not a millimetre, and it needs a finer grid than
# one (RNG-33 CP4). At step 0.1 the per-cut conventional defaults CP1 researched
# do not survive the round trip: cushion's 1.02 lands on 1.00 and marquise's
# 1.95 on 2.00 -- which is exactly the "one shared default makes three of four
# wrong on sight" failure the per-cut bands exist to prevent, reintroduced by a
# rounding rule rather than by a wrong number. The form input carries
# step="0.01" to match; the invariant that every float leaf is rounded to ITS
# OWN form step is what keeps the browser from silently blocking Generate.
RATIO_STEP = 0.01
_FIELD_STEPS = {"length_ratio": RATIO_STEP}
# Groups that can carry stepped dimension fields; confidence/motifs/version/
# archetype are left alone by _round_to_step.
_DIMENSION_GROUPS = ("shank", "setting", "stones", "halo", "trilogy", "side_stone")

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

# Read off the schema rather than restated, so the clamp cannot drift from the
# contract (the same rule `_field_bounds` follows for the archetype groups).
_MAX_LENGTH_RATIO = next(
    (m.le for m in Stones.model_fields["length_ratio"].metadata
     if getattr(m, "le", None) is not None),
    2.5,
)

# The buildable cuts, read off the RingSpec Literal rather than restated, for
# the same reason as `_MAX_LENGTH_RATIO` above: a second hand-written list is a
# second thing to forget when cut #7 lands (docs/adr/0002). `_stone_shape`
# degrades anything not in here to round, so a stale copy would silently throw
# away a cut the geometry can already build -- which is precisely the bug
# RNG-33 exists to fix, reintroduced one layer up.
_BUILDABLE_SHAPES = frozenset(
    get_args(Stones.model_fields["shape"].annotation)
)

# Same rule, same reason, for the shank cross-section (RNG-25): read off the
# RingSpec Literals rather than a second hand-written list.
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
    "`style` to a free-text description of what you actually see (e.g. "
    "'cathedral pave halo'). Set `archetype` to the NEAREST of the four "
    "supported buildable styles: solitaire (a single centre stone), halo (a "
    "ring of small accents around the centre), trilogy (one centre plus two "
    "flanking side stones), or side_stone (a channel row of small accents "
    "down each shoulder). Estimate the dimensions of the chosen archetype's "
    "group (halo_*, side_stone_* for trilogy, accent_* for side_stone). "
    "EVERY field is required: fill in a number for every dimension, and use "
    "0 for any dimension you cannot estimate or that does not apply to the "
    "chosen archetype (e.g. the halo_* fields on a solitaire). Set "
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
    # Shank cross-section (RNG-25). Plain `str`, like `stone_shape` below and
    # for the same ADR-0004 reason: a Literal or optional would add a union
    # param. Degraded in code by `_shank_profile`.
    outer_profile: str
    inner_profile: str
    # Centre-stone shape (RNG-23). Plain `str`/`float`, not a Literal or an
    # optional: either would add a union param, and ADR-0004 keeps this schema
    # flat and required. The value is validated in code, where an unsupported cut
    # degrades to "round" instead of failing the whole classification.
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
    stone_shape: str = "round"
    stone_length_ratio: float = 1.0
    outer_profile: str = "domed"
    inner_profile: str = "domed"

    def to_spec(self) -> dict | None:
        """Assemble a coherent, castable RingSpec (archetype + groups +
        confidence), or None when no ring was detected. See `_coherent_spec`
        for the fallback chain; use `to_json` when the adjustments made along
        the way are also needed."""
        return self._coherent_spec()[0]

    def _coherent_spec(self) -> tuple[dict | None, list[Adjustment]]:
        """Assemble a spec, then repair it against its own casting-gate
        violations (RNG-32) rather than trusting vision's per-field
        estimates to already cohere -- each field is individually clamped to
        its own range in `_assemble`, but nothing there checks a field
        against its siblings (a stone taller than its own head is
        schema-valid on both fields alone).

        Fallback chain, each link a strictly safer bet than the last:
        detected archetype (repaired) -> solitaire from the same shared
        estimates (repaired) -> pure-default solitaire, which is guaranteed
        castable (tests/test_ringspec_coherence.py's
        test_defaults_are_castable_after_coherence). A schema-invalid
        assembly (extreme snapped counts, RNG-19's tightened gate) skips
        straight to the next link rather than repairing garbage."""
        if not self.ring_detected:
            return None, []
        for archetype, group in (
            (self.archetype, self.group_estimates),
            ("solitaire", {}),
        ):
            try:
                spec = self._assemble(archetype, group)
                validate_spec(spec)
            except ValidationError:
                logger.error(
                    "assembled %s spec failed validation; trying next "
                    "fallback", archetype, exc_info=True,
                )
                continue
            coherent, adjustments = make_coherent(spec, self.confidence)
            if is_castable(validate_spec(coherent)):
                stepped = _settle_on_step_grid(coherent)
                if stepped is not None:
                    return stepped, adjustments
                logger.error(
                    "%s spec did not settle on the step grid castably; "
                    "trying next fallback", archetype,
                )
                continue
            logger.error(
                "%s spec still uncastable after repair; trying next "
                "fallback", archetype,
            )
        return self._assemble("solitaire", {}, estimates={}), []

    def _assemble(self, archetype: str, group: dict,
                  estimates: dict | None = None) -> dict:
        """`estimates` defaults to `self.estimates`; the pure-default last
        resort in `_coherent_spec` passes `{}` explicitly to get the
        guaranteed-castable defaults (and a round stone -- shape is skipped
        along with it, since a bad shape reading is exactly the kind of
        thing that resort exists to shed)."""
        est = self.estimates if estimates is None else estimates
        spec = {
            "version": "1.0",
            "archetype": archetype,
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
        if archetype in _ARCHETYPE_GROUPS:
            # Always emit the group key -- an empty dict lets the schema fill
            # every group default (each group field is optional-with-default).
            spec[_ARCHETYPE_GROUPS[archetype][0]] = dict(group)
        return spec

    def to_json(self) -> dict:
        spec, adjustments = self._coherent_spec()
        return {
            "ring_detected": self.ring_detected,
            "detected_style": self.style,
            "note": self.note,
            "spec": spec,
            # RNG-32: fields the repair moved to make the spec castable, so
            # the frontend can flag them alongside the existing low-confidence
            # markers (CP3) -- "estimates only, verify" extends to "and this
            # one was adjusted for buildability".
            "adjustments": [a.model_dump() for a in adjustments],
        }


def _settle_on_step_grid(coherent: dict) -> dict | None:
    """Land `coherent` on the form's 0.1 step grid without breaking
    castability, or return None if none of the three tries manage it (RNG-38).

    Nearest is right almost always. "ceil"/"floor" are a direct castability
    re-check, not another repair pass -- deliberately, since a repair margin
    that ties exactly on a half-step (see _round_to_step) makes
    round-then-re-repair oscillate forever between the same two values,
    where a static "try the other neighbour" terminates in one step. None
    means the caller should fall back further rather than return an
    uncastable spec -- the same "coherence cannot be reached" case
    `_coherent_spec`'s fallback chain already exists for."""
    for direction in ("nearest", "ceil", "floor"):
        stepped = _round_to_step(coherent, direction)
        if is_castable(validate_spec(stepped)):
            return stepped
    return None


_STEP_ROUNDERS = {"nearest": round, "ceil": math.ceil, "floor": math.floor}


def _to_step(value: float, step: float, step_round) -> float:
    """Snap `value` onto the `step` grid, then clean up the binary-float noise
    that multiplying back by a non-representable step reintroduces."""
    return round(step_round(value / step) * step,
                 max(0, -math.floor(math.log10(step) + 1e-9)))


def _round_to_step(spec: dict, direction: str = "nearest") -> dict:
    """Round every float dimension in `spec` to DIMENSION_STEP (RNG-38).

    A generic type-driven walk, not a per-field allowlist: every float leaf
    in a dimension group IS a stepped form field, and every int leaf is
    already step=1 aligned by construction (_snap_prong / _group_estimates's
    int() cast), so there is nothing to special-case. confidence/motifs/
    version/archetype are untouched -- they don't back a stepped input.

    `direction="nearest"` (the default) is right almost always; see
    `_settle_on_step_grid` for why "ceil"/"floor" exist.

    Returns a new dict; does not mutate `spec`."""
    step_round = _STEP_ROUNDERS[direction]
    out = dict(spec)
    for group_key in _DIMENSION_GROUPS:
        group = spec.get(group_key)
        if not isinstance(group, dict):
            continue
        out[group_key] = {
            # round() twice: once to the step count (an integer), once more
            # on the result to clean up the binary-float noise that
            # `n * 0.1` reintroduces (1.9 -> 1.9000000000000001) even when
            # n is exact -- 0.1 has no exact binary representation.
            k: _to_step(v, _FIELD_STEPS.get(k, DIMENSION_STEP), step_round)
            if isinstance(v, float) else v
            for k, v in group.items()
        }
    return out


def _shank_profile(outer: str, inner: str) -> dict:
    """Normalise the vision layer's shank profile into RingSpec's shank
    fields (RNG-25). Each axis degrades independently to `domed` (court, the
    pre-RNG-25 default) rather than failing the whole classification -- the
    same never-500 rule `_stone_shape` follows, simpler here because there is
    no ratio to clamp, only two independent categorical choices."""
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
    """Normalise the vision layer's stone shape into RingSpec's stones fields.

    Degrades rather than fails: a cut we cannot build (princess, trillion,
    heart) becomes a round stone of the same size instead of a spec that fails
    validation. That keeps the never-500 rule and leaves the field editable,
    which the "estimates only" framing already promises. RNG-33 widened the
    buildable set from two shapes to six, so the degrade path is now for genuine
    strangers rather than for most of the catalogue.

    The ratio answers two DIFFERENT questions, and conflating them is what makes
    a marquise render as a lens:

      * **"I could not estimate it"** -- the 0 sentinel (docs/adr/0004 requires
        every schema field, so 0 means absent). That takes the cut's
        CONVENTIONAL default, because a marquise nobody measured is still a
        marquise and 1.0 would hand back a circle wearing the name.
      * **"I estimated it, and it is outside what this cut can be"** -- that
        takes the nearest value the cut CAN be. Vision looked and said "very
        elongated"; snapping to the textbook default would throw that reading
        away, where the band edge keeps it.

    A ratio of 1.0 IS a circle for an OVAL, so an oval that thin is recorded as
    round -- calling it oval would be a claim the geometry then has to
    special-case (RNG-23). That rule is about oval, not about 1.0: a square
    cushion is genuinely 1.00 and still has rounded corners and outward-bowed
    sides, so it stays a cushion.
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
            stone_shape=data.stone_shape,
            stone_length_ratio=data.stone_length_ratio,
            outer_profile=data.outer_profile,
            inner_profile=data.inner_profile,
        )
    except Exception:
        logger.error("classify_ring failed", exc_info=True)
        return _empty(ok=False, ring_detected=False, note="")
