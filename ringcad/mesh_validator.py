"""Reusable mesh validator — the single source of truth for "is this mesh
castable" (lost-wax).

RNG-1 only *detects*; RNG-5 will extend this with auto-repair. Keep the checks
here, not buried in tests, so the backend can call the same logic before
returning an STL.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Tuple, Union

import numpy as np
import trimesh

# Lost-wax casting constraints (mm). Hard manufacturing limits, not UI hints.
MIN_WALL_MM = 0.8
MIN_PRONG_TIP_MM = 0.7

MeshLike = Union[trimesh.Trimesh, str, Path]


@dataclass(frozen=True)
class ValidationResult:
    is_watertight: bool
    non_manifold_edges: int
    body_count: int
    volume_mm3: float
    bounds: Tuple[Tuple[float, float, float], Tuple[float, float, float]]

    @property
    def is_castable(self) -> bool:
        """A castable mesh is a single watertight manifold body."""
        return (
            self.is_watertight
            and self.non_manifold_edges == 0
            and self.body_count == 1
        )


def _as_mesh(obj: MeshLike) -> trimesh.Trimesh:
    if isinstance(obj, trimesh.Trimesh):
        return obj
    mesh = trimesh.load(str(obj), force="mesh")
    if not isinstance(mesh, trimesh.Trimesh):
        raise ValueError(f"could not load a single mesh from {obj!r}")
    return mesh


def count_non_manifold_edges(mesh: trimesh.Trimesh) -> int:
    """Edges not shared by exactly two faces (holes = 1, non-manifold > 2)."""
    if len(mesh.faces) == 0:
        return 0
    edges = np.sort(mesh.edges, axis=1)
    _, counts = np.unique(edges, axis=0, return_counts=True)
    return int(np.count_nonzero(counts != 2))


def count_bodies(mesh: trimesh.Trimesh) -> int:
    """Number of connected components (distinct solids)."""
    if len(mesh.faces) == 0:
        return 0
    components = trimesh.graph.connected_components(
        mesh.face_adjacency, nodes=np.arange(len(mesh.faces))
    )
    return len(components)


def validate_mesh(obj: MeshLike) -> ValidationResult:
    mesh = _as_mesh(obj)
    return ValidationResult(
        is_watertight=bool(mesh.is_watertight),
        non_manifold_edges=count_non_manifold_edges(mesh),
        body_count=count_bodies(mesh),
        volume_mm3=float(abs(mesh.volume)),
        bounds=(tuple(mesh.bounds[0]), tuple(mesh.bounds[1])),
    )
