# RNG-18 — Pin build123d + OCP in requirements.txt

**Type:** fix · **Landed:** 2026-07-20 · *Written after the fact from the project
record; there was no frozen design.*

## Problem

A clean clone could not generate a ring: the geometry kernel's packages were
installed in the working venv but never declared. `pydantic` turned out to be
undeclared too.

## Outcome

**Shipped.** `build123d`, `cadquery-ocp-novtk` (the OpenCASCADE binding, *not*
"OCP") and `pydantic` are declared and pinned; a clean venv installs and runs the
full suite with no manual steps. `tests/test_requirements.py` walks the real AST of
`ringcad/` and fails on any undeclared or unpinned import, so this class of gap
cannot return silently.

**What surprised us.** `pydantic` was undeclared as well, not just the kernel, and
the OpenCASCADE binding is distributed as `cadquery-ocp-novtk`, not "OCP".

**ADRs it left.** None.
