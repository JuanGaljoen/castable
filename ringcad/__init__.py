"""ringcad — geometry rendering + mesh validation for the Ring CAD app.

Reused across tickets: RNG-2 (backend) drives `render` per request, RNG-5
extends `mesh_validator` with auto-repair.
"""
__all__ = ["render", "mesh_validator"]
