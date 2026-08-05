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

    An optional `_cuts` callable yields solids SUBTRACTED after that fuse. A
    module that declares cuts contributes no leaves: `side_stone` (RNG-19 CP3)
    is the first, because a channel setting removes metal from the band rather
    than adding metal to it.
    """

    name: str
    _build: Callable
    _check: Callable
    _parts: Callable | None = None
    _cuts: Callable | None = None

    def build(self, spec: RingSpec, clamps: dict):
        return self._build(spec, clamps)

    def parts(self, spec: RingSpec, clamps: dict) -> list:
        if self._cuts is not None:
            return []
        if self._parts is not None:
            return self._parts(spec, clamps)
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
        _check=_ck.check_gallery,
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

ARCHETYPES: dict[str, list[str]] = {
    "solitaire": ["shank", "seat", "prong_setting"],
    "halo": ["shank", "seat", "prong_setting", "halo"],
    "trilogy": ["shank", "seat", "prong_setting", "trilogy"],
    "side_stone": ["shank", "seat", "prong_setting", "side_stone"],
}


def compose(spec: RingSpec, archetype: str | None = None):
    """Build + fuse an archetype's modules into one build123d solid.

    Fuses every module's LEAF solids in a single general fuse (`leaves[0].fuse(
    *leaves[1:])`). Simple modules contribute one leaf (their fused build);
    heavy modules like `halo` contribute many via `parts`. A single general
    fuse over the flat leaf set is robust where pairwise-fusing pre-fused
    compounds is not (RNG-17 risk #1). Solitaire is unchanged: its three modules
    each yield one leaf, so the fuse is identical to before.
    """
    name = archetype or spec.archetype
    if name not in ARCHETYPES:
        raise UnknownArchetypeError(f"unknown archetype {name!r}")
    c = clamps(spec)
    leaves: list = []
    cuts: list = []
    for mod_name in ARCHETYPES[name]:
        module = MODULES.get(mod_name)
        if module is None:
            raise UnregisteredModuleError(
                f"archetype {name!r} names unregistered module {mod_name!r}"
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
    for cut in cuts:
        solid = solid - cut
    return solid
