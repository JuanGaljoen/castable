"""Parity oracle for the RNG-13 build123d spike.

Renders the canonical OpenSCAD solitaire to STL and reduces any STL to the
three metrics the spike compares on: axis-aligned bounding box, solid volume,
and manifold (watertight) status. Both kernels feed the SAME trimesh reducer,
so the comparison is apples-to-apples.
"""
from __future__ import annotations

import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping

import trimesh

REPO = Path(__file__).resolve().parents[2]
SCAD = REPO / "scad" / "solitaire.scad"

# The 7 canonical solitaire params, matching the SCAD defaults verbatim so the
# two kernels are asked for the identical ring.
DEFAULT_PARAMS: dict[str, float | int] = {
    "inner_diameter": 16.5,
    "band_width": 2.2,
    "band_thickness": 1.9,
    "stone_diameter": 6.5,
    "stone_height": 4,
    "prong_count": 6,
    "setting_height": 6,
}


@dataclass(frozen=True)
class Metrics:
    bbox: tuple[float, float, float]   # (dx, dy, dz) extents, mm
    volume: float                      # mm^3
    watertight: bool
    non_manifold_edges: int

    def describe(self) -> str:
        dx, dy, dz = self.bbox
        return (
            f"bbox=({dx:.3f}, {dy:.3f}, {dz:.3f}) mm  "
            f"volume={self.volume:.2f} mm^3  "
            f"watertight={self.watertight}  "
            f"non_manifold_edges={self.non_manifold_edges}"
        )


def metrics_from_stl(stl_path: Path) -> Metrics:
    mesh = trimesh.load(stl_path, force="mesh")
    ext = mesh.bounding_box.extents
    nme = len(mesh.edges_unique) - len(mesh.face_adjacency)
    return Metrics(
        bbox=(float(ext[0]), float(ext[1]), float(ext[2])),
        # trimesh volume can be tiny-negative on inverted winding; abs is the
        # physical magnitude we care about for parity.
        volume=abs(float(mesh.volume)),
        watertight=bool(mesh.is_watertight),
        non_manifold_edges=int(max(nme, 0)),
    )


def render_openscad(stl_path: Path, params: Mapping[str, object] = DEFAULT_PARAMS,
                    fn: int = 32) -> Metrics:
    """Render the SCAD solitaire to `stl_path` and return its metrics."""
    stl_path.parent.mkdir(parents=True, exist_ok=True)
    cmd = ["openscad", "-o", str(stl_path), "-D", f"$fn={fn}"]
    for key, value in params.items():
        cmd += ["-D", f"{key}={value}"]
    cmd.append(str(SCAD))
    proc = subprocess.run(cmd, capture_output=True, text=True, timeout=180)
    if proc.returncode != 0 or not stl_path.exists():
        raise RuntimeError(f"OpenSCAD render failed:\n{proc.stderr}")
    return metrics_from_stl(stl_path)


if __name__ == "__main__":
    out = REPO / "spikes" / "rng13" / "out"
    m = render_openscad(out / "openscad_solitaire.stl")
    print("OpenSCAD oracle:", m.describe())
