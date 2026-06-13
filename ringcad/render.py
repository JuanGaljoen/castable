"""Headless OpenSCAD render harness.

Wraps the `openscad` CLI the way RNG-2's backend will: inject parameters via
`-D name=value`, render to STL, capture stdout/stderr and timing/size. The
binary is resolved from $OPENSCAD_BIN (default: `openscad` on PATH).
"""
from __future__ import annotations

import os
import shutil
import subprocess
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Mapping, Optional

OPENSCAD_BIN = os.environ.get("OPENSCAD_BIN", "openscad")

# Facet resolution. The SCAD ties mesh density to $fn, so this trades render
# speed vs smoothness without changing topology/castability. 40 keeps the test
# suite fast; hero/preview renders pass a higher $fn for smoothness.
DEFAULT_FN = 28


@dataclass(frozen=True)
class RenderResult:
    returncode: int
    stdout: str
    stderr: str
    stl_path: Path
    seconds: float
    size_bytes: int

    @property
    def ok(self) -> bool:
        return self.returncode == 0 and self.size_bytes > 0

    @property
    def messages(self) -> str:
        """Combined OpenSCAD output (echo warnings + render stats)."""
        return f"{self.stdout}\n{self.stderr}"


def openscad_available() -> bool:
    return shutil.which(OPENSCAD_BIN) is not None


def _fmt(value: object) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    return str(value)


def render_scad(
    scad_path: os.PathLike | str,
    stl_path: os.PathLike | str,
    params: Optional[Mapping[str, object]] = None,
    fn: Optional[int] = DEFAULT_FN,
    timeout: float = 120,
) -> RenderResult:
    """Render `scad_path` to `stl_path`, overriding `params` via -D.

    Returns a RenderResult even on failure (returncode != 0) so callers can
    inspect stderr — mirrors RNG-2 returning OpenSCAD stderr on a 400.
    """
    scad_path = Path(scad_path)
    stl_path = Path(stl_path)
    stl_path.parent.mkdir(parents=True, exist_ok=True)

    cmd = [OPENSCAD_BIN, "-o", str(stl_path)]
    if fn is not None:
        cmd += ["-D", f"$fn={fn}"]
    for key, value in (params or {}).items():
        cmd += ["-D", f"{key}={_fmt(value)}"]
    cmd.append(str(scad_path))

    start = time.perf_counter()
    proc = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
    seconds = time.perf_counter() - start

    size = stl_path.stat().st_size if stl_path.exists() else 0
    return RenderResult(
        returncode=proc.returncode,
        stdout=proc.stdout,
        stderr=proc.stderr,
        stl_path=stl_path,
        seconds=seconds,
        size_bytes=size,
    )
