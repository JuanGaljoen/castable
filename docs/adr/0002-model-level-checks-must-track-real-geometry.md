# 2. Model-level castability proxies must be retired once real geometry checks exist

- **Status:** Accepted
- **Date:** 2026-07-08
- **Context ticket:** RNG-9 CP4 (endpoint wire-up); the checked spec is CP1's
  `HaloSpec` castability gate, superseded by CP2/CP3 geometry.

## Context

CP1 shipped `validate_castability()` (`ringcad/ringspec/castability.py`) as a
pre-geometry gate: cheap, field-only formulas run on the RingSpec before any
build123d solid exists, so obviously-bad input 400s fast. For the halo
archetype, two of its checks — `_halo_wall` (required `halo_gap >=
MIN_WALL_MM`) and `_halo_accent_tip` (`min(diameter, height) * 0.5 >=
MIN_PRONG_TIP_MM`) — were explicit placeholders, commented "fuzzy... pending a
pin against real geometry" and "CP2 will pin it against real halo geometry."

CP2 and CP3 then built the real thing: the `gallery` primitive and
`accent_seat`/`accent_prong`, each with its own in-kernel `check_*` self-check
that measures the *actual* B-rep wall/tip on the *actual* construction — not a
field-derived guess. Critically, both are castable **by construction**: the
gallery's rail/bridge walls are sized from fixed minima independent of
`halo_gap`, and the accent seat/prong walls are sized from their own
construction margins, not from `min(diameter, height) * 0.5`. CP3's own test
suite (`tests/test_halo_watertight.py`'s BAND) proves this across the full
declared field range.

Nobody went back and removed the CP1 placeholders once CP2/CP3 made them
obsolete. RNG-9 CP4 (wiring `/generate-ring` to dispatch a structured halo
RingSpec through `validate_castability` → `compose()`) was the first caller to
actually exercise the full path end-to-end on the golden halo — the exact
defaults documented in `specs/RNG-9.md` (`halo_gap=0.5`,
`halo_stone_diameter=1.3`, `halo_stone_height=1.2`). It 400'd. The two stale
proxies rejected the spec's own canonical example, even though CP3's raw
`compose()` output for that identical spec is a proven single watertight
manifold with clean self-checks.

## Decision

Removed `_halo_wall` and `_halo_accent_tip` from `validate_castability()`.
Kept `_halo_overcrowding` — it checks a genuine cross-field relationship (arc
spacing between neighbouring accents) that construction does not guard
against, so it is not superseded by anything CP2/CP3 built.

**The general rule going forward:** a model-level proxy check is a stand-in
for real geometry, valid only until real geometry exists. When a module's
build becomes castable *by construction* and grows its own in-kernel
`check_*`, audit any pre-geometry proxy that shaped the same failure mode —
either delete it (if construction now guarantees the floor) or reformulate it
against the real construction math (if the proxy still earns its keep as a
fast pre-geometry reject). Do not leave both a stale proxy and a correct
in-kernel check disagreeing on the same input; the gate that runs first (the
model-level one, since it runs before any solid is built) wins, silently
overriding the more accurate check.

## Consequences

- `/generate-ring`'s golden-halo defaults are now castable through the full
  dispatch path, matching CP3's own claim.
- `tests/test_ringspec_halo_castability.py` was rewritten to test only
  `_halo_overcrowding` plus a regression assertion that the golden defaults
  produce zero violations — the CP1-era wall/tip-proxy tests were deleted
  along with the code they pinned.
- **Standing gap, not addressed here:** the in-kernel `check_*` self-checks
  (`check_gallery`, `check_accent_seat`, `check_accent_prong`, and the
  solitaire-side `check_shank`/`check_seat`/`check_prong_setting`) are still
  not wired into `compose()` or the endpoint anywhere — they run only in their
  own unit tests. The only production-path castability gates today are (a)
  the model-level `validate_castability()` proxies pre-geometry and (b) the
  post-export trimesh `validate_and_repair` mesh check. Wiring the in-kernel
  checks into a runtime gate (per RNG-16 AC4's original "augments the mesh
  gate" framing) is future work, not decided or scheduled here.
