# Solitaire Ring — Sane Parameter Ranges (RNG-1)

Feeds **RNG-3**'s form defaults and input bounds. Values outside "Sane range"
still render a castable mesh (inputs are clamped by construction) but may look
ungainly. Defaults below match the reference CAD drawing (6-prong, tapered
shank, US6).

| Parameter        | Default | Sane range (UI bounds) | Hard floor (clamp) | Notes |
|------------------|---------|------------------------|--------------------|-------|
| `inner_diameter` | 16.5 mm | 14 - 23 mm             | 5 mm               | 16.5 ≈ US6 |
| `band_width`     | 2.2 mm  | 1.6 - 6 mm             | 0.8 mm (MIN_WALL)  | shank width along finger axis, at the base |
| `band_thickness` | 1.9 mm  | 0.8 - 4 mm             | 0.8 mm (MIN_WALL)  | radial thickness at the base; flares toward the head |
| `stone_diameter` | 6.5 mm  | 2 - 10 mm              | 1 mm               | basket / seat diameter; warns at >= 0.9 x inner_diameter; castable to 24 mm |
| `stone_height`   | 4 mm    | 2 - 6 mm               | 0.5 mm             | influences claw rise |
| `prong_count`    | 6       | {4, 6}                 | snaps to 4         | dropdown only; other values warn + snap to 4 |
| `setting_height` | 6 mm    | 3 - 8 mm               | 0.8 mm (MIN_WALL)  | head height: band shoulder -> prong tip |

### Extra shaping control (beyond the canonical 7)
| Parameter      | Default | Range     | Notes |
|----------------|---------|-----------|-------|
| `shank_taper`  | 1.7     | 1.0 - 2.0 | cross-section scale at the head shoulder vs the base; 1.0 = no taper |

## Halo accent (RNG-9, HaloSpec only)
The accent-stone ring encircling the centre stone. Ranges are structural sanity
caps; casting floors are enforced in `validate_castability`, not the UI.

| Parameter             | Default | Sane range | Castability floor / note |
|-----------------------|---------|------------|--------------------------|
| `halo_stone_diameter` | 1.3 mm  | 0.9 - 2.5 mm | floor keeps the derived accent retaining tip >= 0.7 mm (MIN_PRONG_TIP) |
| `halo_stone_count`    | 14      | 8 - 24     | overcrowding check: per-accent arc must exceed the accent diameter |
| `halo_gap`            | 0.5 mm  | 0.3 - 1.5 mm | guards the 0.8 mm (MIN_WALL) metal wall between accents |
| `halo_stone_height`   | 1.2 mm  | 0.8 - 3.0 mm | feeds the accent-tip proxy alongside diameter |

## Casting invariants (always hold, any input)
- Min wall thickness **0.8 mm** (band, seat ring, claw wires).
- Min prong tip diameter **0.7 mm**.
- Single watertight manifold, zero non-manifold edges.

## Resolution vs render cost
Mesh density scales with `$fn` (`RES_A`, `RES_B`, `WFN`, `CFN` in the SCAD), so
topology / castability is identical at any `$fn` — only smoothness and render
time change:
- **Tests / default render:** `$fn = 28` (`render.py` `DEFAULT_FN`) ≈ 35–50 s per
  STL on this machine. The slow part is the basket boolean union, not the band.
- **Hero previews:** PNG export uses OpenSCAD's fast preview renderer (~2-3 s even
  at `$fn = 96`), so previews can be smooth and cheap.
- **Golden / casting STL:** render at higher `$fn` (e.g. 72) for a smooth export.
Tighten later (RNG-2 latency) by lowering `$fn` or simplifying the basket union.
