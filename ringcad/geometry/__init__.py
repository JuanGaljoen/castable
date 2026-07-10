"""build123d solitaire geometry (RNG-15).

Decomposed module library — `shank`, `prong_setting`, `seat` — composed by
`build_solitaire`, with STL/STEP byte exporters. Ported faithfully from the
RNG-13 spike so OpenSCAD parity holds; casting constants come from
`ringcad.mesh_validator`.
"""
from .accent_prong import accent_prong
from .accent_seat import accent_seat
from .bezel import bezel
from .export import to_step_bytes, to_stl_bytes
from .gallery import gallery
from .halo import halo
from .module import (
    ARCHETYPES,
    MODULES,
    ComposeError,
    DegenerateModuleError,
    Module,
    SimpleModule,
    UnknownArchetypeError,
    UnregisteredModuleError,
    compose,
)
from .prong_setting import prong_setting
from .seat import seat
from .shank import shank
from .side_stone import side_stone
from .solitaire import build_solitaire
from .trilogy import trilogy

__all__ = [
    "build_solitaire",
    "compose",
    "shank",
    "prong_setting",
    "seat",
    "bezel",
    "gallery",
    "halo",
    "trilogy",
    "side_stone",
    "accent_seat",
    "accent_prong",
    "to_stl_bytes",
    "to_step_bytes",
    "MODULES",
    "ARCHETYPES",
    "Module",
    "SimpleModule",
    "ComposeError",
    "UnknownArchetypeError",
    "UnregisteredModuleError",
    "DegenerateModuleError",
]
