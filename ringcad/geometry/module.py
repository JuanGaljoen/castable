"""Module library: the generic module interface + registry + compose (RNG-16).

A `Module` is a named unit that builds a build123d solid from its RingSpec slice
and self-checks the result for castability. `SimpleModule` adapts the existing
free functions (shank / seat / prong_setting / bezel) to that interface. The
`MODULES` registry maps name -> Module; `ARCHETYPES` maps an archetype name to
an ordered module list. `compose` builds and fuses an archetype's modules.

Production ships only the "solitaire" archetype; new archetypes (and modules)
register at runtime without editing any existing module file (AC6).
"""
from __future__ import annotations

import functools
from dataclasses import dataclass
from typing import Callable, Protocol, runtime_checkable

from ringcad.ringspec import RingSpec, Violation

from . import _castability as _ck
from ._common import clamps
from .bezel import bezel
from .halo import halo, halo_parts
from .prong_setting import prong_setting
from .seat import seat
from .shank import shank
from .side_stone import side_stone, side_stone_cuts
from .trilogy import trilogy, trilogy_parts


@runtime_checkable
class Module(Protocol):
    """A named, composable geometry unit."""

    name: str

    def build(self, spec: RingSpec, clamps: dict): ...

    def parts(self, spec: RingSpec, clamps: dict) -> list: ...

    def cuts(self, spec: RingSpec, clamps: dict) -> list: ...

    def check(self, solid, spec: RingSpec, clamps: dict) -> list[Violation]: ...


@dataclass(frozen=True)
class SimpleModule:
    """Adapts free build/check callables to the Module interface.

    An optional `_parts` callable yields the module's leaf solids UN-fused so
    `compose` can flat-fuse them in one general fuse (robust for heavy modules
    like `halo`; see `halo_parts`). Modules without it contribute one leaf:
    their fused `build` result.

    An optional `_cuts` callable yields solids SUBTRACTED after that fuse.
    Modules come in both shapes:

      - cut-only — `side_stone` (RNG-19 CP3) declares cuts and no parts, because
        a channel setting removes metal from the band rather than adding to it;
      - parts AND cuts — `halo` (RNG-19 CP4) builds a plate and then bores the
        accent seats out of it.

    So `_parts` and `_cuts` are independent: declaring cuts does not suppress
    leaves. Only a module with `_cuts` and no `_parts` contributes nothing to
    the fuse.
    """

    name: str
    _build: Callable
    _check: Callable
    _parts: Callable | None = None
    _cuts: Callable | None = None

    def build(self, spec: RingSpec, clamps: dict):
        return self._build(spec, clamps)

    def parts(self, spec: RingSpec, clamps: dict) -> list:
        if self._parts is not None:
            return self._parts(spec, clamps)
        if self._cuts is not None:
            return []
        return [self._build(spec, clamps)]

    def cuts(self, spec: RingSpec, clamps: dict) -> list:
        if self._cuts is None:
            return []
        return self._cuts(spec, clamps)

    def check(self, solid, spec: RingSpec, clamps: dict) -> list[Violation]:
        return self._check(solid, spec, clamps)


class ComposeError(ValueError):
    """Base for all compose() failures."""


class UnknownArchetypeError(ComposeError):
    """The requested archetype is not registered in ARCHETYPES."""


class UnregisteredModuleError(ComposeError):
    """An archetype names a module absent from MODULES."""


class DegenerateModuleError(ComposeError):
    """A module produced no solid / non-positive volume."""


MODULES: dict[str, Module] = {
    "shank": SimpleModule(
        name="shank",
        _build=lambda spec, c: shank(spec, c),
        _check=_ck.check_shank,
    ),
    "seat": SimpleModule(
        name="seat",
        _build=lambda spec, c: seat(spec, c),
        _check=_ck.check_seat,
    ),
    "prong_setting": SimpleModule(
        name="prong_setting",
        _build=lambda spec, c: prong_setting(spec, c),
        _check=_ck.check_prong_setting,
    ),
    "bezel": SimpleModule(
        name="bezel",
        _build=lambda spec, c: bezel(spec, c),
        _check=_ck.check_bezel,
    ),
    "halo": SimpleModule(
        name="halo",
        _build=lambda spec, c: halo(spec, c),
        _check=_ck.check_halo_plate,
        _parts=lambda spec, c: halo_parts(spec, c),
    ),
    "trilogy": SimpleModule(
        name="trilogy",
        _build=lambda spec, c: trilogy(spec, c),
        _check=_ck.check_trilogy,
        _parts=lambda spec, c: trilogy_parts(spec, c),
    ),
    "side_stone": SimpleModule(
        name="side_stone",
        _build=lambda spec, c: side_stone(spec, c),
        _check=_ck.check_side_stone,
        _cuts=lambda spec, c: side_stone_cuts(spec, c),
    ),
}

# Kept for callers that want to FORCE a specific module list regardless of
# what the spec's own feature groups say (e.g. building the bare band for a
# before/after comparison) — `compose(spec, archetype=...)`. The spec-driven
# path (no override) no longer consults this: RNG-24 CP2 composes from
# whichever feature groups are actually present, any subset, not a choice of
# exactly one archetype (`_spec_module_names`).
BASE_MODULES: list[str] = ["shank", "seat", "prong_setting"]
_FEATURE_MODULES: tuple[str, ...] = ("halo", "trilogy", "side_stone")
ARCHETYPES: dict[str, list[str]] = {
    "solitaire": BASE_MODULES,
    "halo": BASE_MODULES + ["halo"],
    "trilogy": BASE_MODULES + ["trilogy"],
    "side_stone": BASE_MODULES + ["side_stone"],
}


def _spec_module_names(spec: RingSpec) -> list[str]:
    """The module list a spec's OWN feature groups imply — any subset of
    {halo, trilogy, side_stone} alongside the base three, not a single
    archetype choice (RNG-24 CP2)."""
    return BASE_MODULES + [
        name for name in _FEATURE_MODULES if getattr(spec, name) is not None
    ]


def compose(spec: RingSpec, archetype: str | None = None):
    """Build + fuse a spec's modules into one build123d solid.

    Fuses every module's LEAF solids in a single general fuse (`leaves[0].fuse(
    *leaves[1:])`). Simple modules contribute one leaf (their fused build);
    heavy modules like `halo` contribute many via `parts`. A single general
    fuse over the flat leaf set is robust where pairwise-fusing pre-fused
    compounds is not (RNG-17 risk #1). A bare solitaire is unchanged: its three
    modules each yield one leaf, so the fuse is identical to before.

    `archetype`, when given, FORCES that named module list instead of reading
    the spec's own feature groups (back-compat for callers building a bare
    comparison band, e.g. `compose(spec, archetype="solitaire")`).
    """
    if archetype is not None:
        if archetype not in ARCHETYPES:
            raise UnknownArchetypeError(f"unknown archetype {archetype!r}")
        mod_names = ARCHETYPES[archetype]
    else:
        mod_names = _spec_module_names(spec)
    c = clamps(spec)
    leaves: list = []
    cuts: list = []
    for mod_name in mod_names:
        module = MODULES.get(mod_name)
        if module is None:
            raise UnregisteredModuleError(
                f"module list names unregistered module {mod_name!r}"
            )
        parts = module.parts(spec, c)
        mod_cuts = module.cuts(spec, c)
        # A module must contribute SOMETHING: metal, or a cut. Each is checked
        # for positive volume — a zero-volume cut is as much a silent no-op as
        # a zero-volume leaf, and docs/adr/0005 is about exactly that class of
        # nothing-happened bug reporting success.
        if not parts and not mod_cuts:
            raise DegenerateModuleError(
                f"module {mod_name!r} produced neither geometry nor a cut"
            )
        for group, label in ((parts, "solid"), (mod_cuts, "cut")):
            if group and (any(p is None for p in group)
                          or sum(p.volume for p in group) <= 0):
                raise DegenerateModuleError(
                    f"module {mod_name!r} produced a degenerate {label}"
                )
        leaves.extend(parts)
        cuts.extend(mod_cuts)
    solid = leaves[0].fuse(*leaves[1:])
    if not cuts:
        return solid
    return _subtract(solid, cuts)


def _subtract(solid, cuts):
    """Apply every cut tool, and CHECK that the subtraction did what it claimed.

    Neither cutting strategy is universally safe, and each fails in the way the
    other survives:

      * ONE n-ary `cut(*tools)` is what RNG-19 adopted, because iterating raised
        `Null TopoDS_Shape` on a 13-accent halo. It is still the default here.
      * But on a side-stone band with an ELONGATED centre stone the n-ary cut
        fails SILENTLY and catastrophically: measured, a marquise centre went
        from a 376.95mm3 single solid to 9.25mm3 in 8 pieces -- the tools
        removed 98% of the ring -- and a pear shattered into 13 solids while
        removing LESS metal than it should have. Cutting iteratively returned a
        correct single solid in every one of those cases.

    So the strategy is chosen by RESULT rather than by guess: take the n-ary
    cut, and if it did not leave exactly one solid, try iteratively and keep
    that instead if it did better. This is docs/adr/0005's rule (assert what the
    boolean produced, do not trust that it succeeded) turned into a recovery
    rather than only an assertion.

    NOT introduced by the new cuts: an `oval` at length_ratio 2.5 on a
    side-stone band fails identically on the pre-RNG-33 tree (2982 mesh bodies,
    2712 non-manifold edges) and the casting gate calls it castable. The new
    cuts only made it reachable at a DEFAULT ratio rather than at the extreme of
    the oval range.
    """
    result = solid.cut(*cuts)
    if len(result.solids()) == 1:
        return result
    try:
        alt = functools.reduce(lambda body, tool: body.cut(tool), cuts, solid)
    except Exception:                                   # pragma: no cover
        return result
    return alt if len(alt.solids()) == 1 else result
