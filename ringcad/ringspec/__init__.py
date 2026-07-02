"""RingSpec v1 — the versioned, typed contract between vision and geometry.

Public surface for RNG-14. Models + schema validation live in `models`, the
7-param round-trip adapters in `adapters`, and the lost-wax castability gate in
`castability`. See docs/ringspec/contract.md for the full contract.
"""
from __future__ import annotations

from .adapters import (
    DEFAULT_SHANK_TAPER,
    PARAM_KEYS,
    from_params,
    to_params,
)
from .castability import Violation, is_castable, validate_castability
from .models import (
    FieldConfidence,
    Halo,
    HaloSpec,
    Motif,
    RingSpec,
    Setting,
    Shank,
    SolitaireSpec,
    SPEC_VERSION,
    Stones,
    spec_errors,
    validate_spec,
)

__all__ = [
    "RingSpec",
    "SolitaireSpec",
    "HaloSpec",
    "Halo",
    "Shank",
    "Setting",
    "Stones",
    "Motif",
    "FieldConfidence",
    "SPEC_VERSION",
    "validate_spec",
    "spec_errors",
    "from_params",
    "to_params",
    "PARAM_KEYS",
    "DEFAULT_SHANK_TAPER",
    "validate_castability",
    "is_castable",
    "Violation",
]
