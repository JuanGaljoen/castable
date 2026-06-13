"""Unit tests for the reusable mesh validator (no OpenSCAD required).

The validator is the single source of truth for "is this mesh castable" and is
reused by RNG-2 (backend) and extended by RNG-5 (auto-repair), so it is tested
in isolation with synthetic trimesh primitives.
"""
import numpy as np
import trimesh

from ringcad.mesh_validator import validate_mesh


def test_watertight_box_is_castable():
    mesh = trimesh.creation.box(extents=(2, 2, 2))
    result = validate_mesh(mesh)
    assert result.is_watertight
    assert result.non_manifold_edges == 0
    assert result.body_count == 1
    assert result.is_castable


def test_two_disjoint_boxes_report_two_bodies_and_not_castable():
    a = trimesh.creation.box(extents=(1, 1, 1))
    b = trimesh.creation.box(extents=(1, 1, 1))
    b.apply_translation([5, 0, 0])
    mesh = trimesh.util.concatenate([a, b])
    result = validate_mesh(mesh)
    assert result.body_count == 2
    assert not result.is_castable


def test_open_mesh_is_not_watertight_and_not_castable():
    mesh = trimesh.creation.box(extents=(2, 2, 2))
    keep = np.ones(len(mesh.faces), dtype=bool)
    keep[0] = False  # drop a face -> open hole
    mesh.update_faces(keep)
    result = validate_mesh(mesh)
    assert not result.is_watertight
    assert not result.is_castable
