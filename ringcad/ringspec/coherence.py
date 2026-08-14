"""Cross-field coherence repair for vision-assembled specs (RNG-32).

`ClassifyResult.to_spec()` clamps each estimate to its own valid range but
never checks a field against its siblings, so vision can emit a spec that is
schema-valid and individually defensible yet physically impossible (a 5.2mm
stone in a 3.0mm head). `make_coherent` closes that gap by repairing whatever
`validate_castability` itself flags, rather than a parallel table of
containment rules -- every `Violation` already names the field to move and
the value it must reach, so a rule added to the gate is covered here for
free.
"""
from __future__ import annotations

import math

from pydantic import BaseModel, ConfigDict

from .castability import Violation, validate_castability
from .models import Halo, SideStone, Setting, Shank, Stones, Trilogy
from .models import validate_spec

MAX_PASSES = 6
_MARGIN_GROW = 1.03
_MARGIN_SHRINK = 0.97

# Dotted-path group prefix -> the Pydantic model that owns its bounds (mirrors
# classify.py's _ARCHETYPE_GROUPS, but keyed by group name rather than
# archetype -- coherence runs after assembly and does not know the archetype
# tag, only the field paths the gate names).
_GROUP_MODELS = {
    "shank": Shank,
    "setting": Setting,
    "stones": Stones,
    "halo": Halo,
    "trilogy": Trilogy,
    "side_stone": SideStone,
}


class Adjustment(BaseModel):
    """A single field the repair loop moved to reach a castable spec."""

    model_config = ConfigDict(extra="forbid")

    field: str
    code: str
    old_value: float
    new_value: float


def _get(spec: dict, path: str):
    obj = spec
    parts = path.split(".")
    for part in parts[:-1]:
        obj = obj[part]
    return obj[parts[-1]]


def _set(spec: dict, path: str, value) -> None:
    obj = spec
    parts = path.split(".")
    for part in parts[:-1]:
        obj = obj[part]
    obj[parts[-1]] = value


def _bounds(path: str) -> tuple[float | None, float | None]:
    """Read (ge, le) off the Pydantic field this path names -- the same
    source of truth classify.py's `_field_bounds` reads from."""
    group, name = path.split(".")
    model_cls = _GROUP_MODELS[group]
    lo = hi = None
    for meta in model_cls.model_fields[name].metadata:
        if hasattr(meta, "ge"):
            lo = meta.ge
        if hasattr(meta, "le"):
            hi = meta.le
    return lo, hi


def _clamp(path: str, value: float) -> float:
    lo, hi = _bounds(path)
    if lo is not None:
        value = max(lo, value)
    if hi is not None:
        value = min(hi, value)
    return value


def _scale(current: float, limit_mm: float, actual_mm: float,
           inverse: bool, additive: bool = False) -> float:
    """Move `current` by the amount the violation's own numbers imply,
    nudged a little further so re-validation clears the boundary rather
    than landing on it.

    `inverse=True` when the field moves OPPOSITE to `actual_mm` (a higher
    accent count means LESS arc between accents) -- multiplicative, exact
    when the two are inversely proportional (they are, for every inverse
    case in the table: arc = perimeter / count).

    `additive=True` when `current` is only one small mm term feeding a
    larger geometric `actual_mm` (a gap feeding a chord alongside the two
    stone radii) -- multiplying a 0.3mm gap by the chord/clearance ratio
    barely moves it, since that ratio is close to 1 at these magnitudes.
    Applying the mm shortfall directly to the field is closer, but the
    field's true sensitivity (an arc-to-chord cosine term) is below 1 and
    falls further as the gap grows, so a 1:1 mm-for-mm correction still
    undershoots and decays geometrically over passes rather than landing.
    Overshoot generously (3x the shortfall, still bounded by the field's own
    schema range) and let re-validation confirm it landed rather than
    computing the exact sensitivity here. Only used where growing the field
    grows `actual_mm` (no additive+inverse case exists in the table)."""
    if additive:
        return current + (limit_mm - actual_mm) * 3.0
    ratio = (actual_mm / limit_mm) if inverse else (limit_mm / actual_mm)
    nudge = _MARGIN_GROW if ratio >= 1 else _MARGIN_SHRINK
    return current * ratio * nudge


def _progress_int(old: int, new: float) -> int:
    """Round toward the direction of travel, guaranteeing the pass makes
    progress even when the scale rounds back to the starting value."""
    if new < old:
        rounded = math.floor(new)
        return rounded if rounded != old else old - 1
    if new > old:
        rounded = math.ceil(new)
        return rounded if rounded != old else old + 1
    return old


def _repair_scaled(spec: dict, v: Violation, *, field: str | None = None,
                    inverse: bool, as_int: bool,
                    additive: bool = False) -> Adjustment:
    field = field or v.field
    old = _get(spec, field)
    new = _scale(float(old), v.limit_mm, v.actual_mm, inverse=inverse,
                 additive=additive)
    new = _progress_int(int(old), new) if as_int else new
    new = _clamp(field, new)
    _set(spec, field, new)
    return Adjustment(field=field, code=v.code, old_value=old, new_value=new)


def _repair_stone_exceeds_head(spec: dict, v: Violation,
                                confidence: dict) -> Adjustment:
    """Ambiguous victim: raise `setting_height` (default) or lower
    `stone_height` -- whichever field vision was LESS sure about moves."""
    conf_stone = confidence.get("stone_height")
    conf_setting = confidence.get("setting_height")
    move_stone = (
        conf_stone is not None and conf_setting is not None
        and conf_stone < conf_setting
    )
    if move_stone:
        old = _get(spec, "stones.stone_height")
        new = _clamp("stones.stone_height",
                      _get(spec, "setting.setting_height") - 0.05)
        _set(spec, "stones.stone_height", new)
        return Adjustment(field="stones.stone_height", code=v.code,
                           old_value=old, new_value=new)
    old = _get(spec, "setting.setting_height")
    new = _clamp("setting.setting_height",
                 _get(spec, "stones.stone_height") + 0.05)
    _set(spec, "setting.setting_height", new)
    return Adjustment(field="setting.setting_height", code=v.code,
                       old_value=old, new_value=new)


def _repair_min_prong_tip(spec: dict, v: Violation,
                           confidence: dict) -> Adjustment:
    """Ambiguous victim: drop to 4 prongs (default, when not already 4) or
    grow `stone_diameter` -- whichever field vision was LESS sure about
    moves. Tip is linear in diameter, so the violation's own limit/actual
    ratio applies exactly to the diameter, not just approximately."""
    prong_count = _get(spec, "setting.prong_count")
    conf_prong = confidence.get("prong_count")
    conf_diam = confidence.get("stone_diameter")
    prefer_diameter = (
        conf_prong is not None and conf_diam is not None
        and conf_prong > conf_diam
    )
    if prong_count != 4 and not prefer_diameter:
        _set(spec, "setting.prong_count", 4)
        return Adjustment(field="setting.prong_count", code=v.code,
                           old_value=prong_count, new_value=4)
    return _repair_scaled(spec, v, field="stones.stone_diameter",
                           inverse=False, as_int=False)


def _repair_side_stone_overcrowding(spec: dict, v: Violation,
                                     confidence: dict) -> Adjustment:
    """Two sub-violations share one code (castability.py's
    `_side_stone_overcrowding`): the row overruns its shoulder span
    (field=accent_count_per_side) or adjacent accents collide
    (field=accent_gap). Both are DIRECT -- more count or more gap both
    increase the measured arc/chord -- so the shared scale formula applies
    to either; only the int-rounding differs."""
    as_int = v.field.endswith("accent_count_per_side")
    return _repair_scaled(spec, v, inverse=False, as_int=as_int,
                           additive=not as_int)


_REPAIRS = {
    "min_wall": lambda s, v, c: _repair_scaled(s, v, inverse=False, as_int=False),
    "stone_exceeds_bore": lambda s, v, c: _repair_scaled(
        s, v, inverse=False, as_int=False),
    "stone_exceeds_head": _repair_stone_exceeds_head,
    "min_prong_tip": _repair_min_prong_tip,
    "stone_curvature": lambda s, v, c: _repair_scaled(
        s, v, inverse=True, as_int=False),
    "halo_overcrowding": lambda s, v, c: _repair_scaled(
        s, v, inverse=True, as_int=True),
    "halo_web": lambda s, v, c: _repair_scaled(s, v, inverse=True, as_int=True),
    "trilogy_overcrowding": lambda s, v, c: _repair_scaled(
        s, v, inverse=False, as_int=False, additive=True),
    "side_stone_overcrowding": _repair_side_stone_overcrowding,
    "side_stone_channel_fit": lambda s, v, c: _repair_scaled(
        s, v, inverse=False, as_int=False),
    "side_stone_channel_floor": lambda s, v, c: _repair_scaled(
        s, v, inverse=False, as_int=False),
}


def make_coherent(spec: dict, confidence: dict | None = None
                   ) -> tuple[dict, list[Adjustment]]:
    """Repair `spec` against its own casting-gate violations until castable
    or the pass budget runs out.

    `spec` must already be schema-valid (raises whatever `validate_spec`
    raises otherwise) -- schema fallback stays the caller's job. Returns the
    (possibly still-violating, if the budget or an unrepairable code was hit)
    working spec as a plain dict, plus every adjustment made, in order. The
    caller decides what "still violating" means for it (fall back further).
    """
    confidence = confidence or {}
    model = validate_spec(spec)
    working = model.model_dump(mode="python")
    adjustments: list[Adjustment] = []
    for _ in range(MAX_PASSES):
        violations = validate_castability(model)
        if not violations:
            break
        repair = _REPAIRS.get(violations[0].code)
        if repair is None:
            break
        adjustments.append(repair(working, violations[0], confidence))
        model = validate_spec(working)
    return working, adjustments
