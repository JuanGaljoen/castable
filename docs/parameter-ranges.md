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

### Centre-stone shape (RNG-23)
| Parameter      | Default | Range            | Notes |
|----------------|---------|------------------|-------|
| `shape`        | `round` | {`round`, `oval`}| omitted means `round`, so every pre-RNG-23 spec is unchanged |
| `length_ratio` | 1.0     | 1.0 - 2.5        | long axis / short axis; 1.0 is round |

With `shape: oval`, **`stone_diameter` is the SHORT axis** (the width) and the long
axis is `stone_diameter * length_ratio`. The long axis runs along the finger
(N-S), the conventional oval setting.

Two consequences worth knowing before choosing a ratio:

- **Elongation thins the tips.** An ellipse's tightest bend is
  `semi_minor^2 / semi_major`, so raising `length_ratio` sharpens the apex where
  the min-wall floor is hardest to hold. That is what caps the range at 2.5.
- **Elongation costs trilogy clearance.** The side stones flank along the same
  axis the oval is longest on, so an oval centre reaches further toward them than
  a round one of equal `stone_diameter` and can trip the overcrowding check.

Prongs are placed so the tips fall midway between adjacent claws (the
conventional 10-2-4-8 layout at 4 prongs), keeping every claw off the
high-curvature apex. A halo follows the same outline, with its accents spaced by
arc length so they do not bunch at the tips.

The vision layer estimates both fields from a photo. It reports `oval` only when
the stone is visibly longer than wide, answers `round` for any cut it cannot
build (emerald, pear, cushion, marquise) or is unsure of, and estimates
`length_ratio` as a ratio rather than in millimetres, since a ratio is what a
photo actually shows.

## Halo accent (RNG-9, HaloSpec only)
The accent-stone ring encircling the centre stone. Ranges are structural sanity
caps; casting floors are enforced by construction in the `gallery`/
`accent_seat`/`accent_prong` geometry (see docs/adr/0002), not by a model-level
proxy.

| Parameter             | Default | Sane range | Castability floor / note |
|-----------------------|---------|------------|--------------------------|
| `halo_stone_diameter` | 1.3 mm  | 0.9 - 2.5 mm | accent retaining tip held >= 0.7 mm (MIN_PRONG_TIP) by construction |
| `halo_stone_count`    | 14      | 8 - 24     | overcrowding check: per-accent arc must exceed the accent diameter |
| `halo_gap`            | 0.5 mm  | 0.3 - 1.5 mm | stone-to-stone spacing; the gallery rail wall beneath is a fixed construction margin, independent of this field |
| `halo_stone_height`   | 1.2 mm  | 0.8 - 3.0 mm | drives the accent bearing well depth |

## Trilogy side stones (RNG-10, TrilogySpec only)
Two symmetric side stones flanking the centre stone, each on its own
`accent_seat` + `accent_prong` setting riding a gallery-post pedestal into the
shank shoulder. Ranges are structural sanity caps; wall/tip floors are
enforced by construction (reusing the same accent primitives as halo).

| Parameter             | Default | Sane range | Castability floor / note |
|-----------------------|---------|------------|--------------------------|
| `side_stone_diameter` | 2.5 mm  | 0.9 - 6.0 mm | side-prong tip held >= 0.7 mm (MIN_PRONG_TIP) by construction |
| `side_stone_height`   | 1.8 mm  | 0.8 - 4.0 mm | drives the side-seat bearing well depth |
| `side_stone_gap`      | 0.6 mm  | 0.3 - 2.0 mm | centre-to-side spacing; `trilogy_overcrowding` guards against oversized side stones on a small shoulder colliding with the centre stone (see docs/ringspec/contract.md) |

## Side-stone band (RNG-11, SideStoneSpec only)
A channel-set accent row down each shoulder of the shank, symmetric about the
centre stone, stopping before the ring base. Ranges are structural sanity
caps; wall floors are enforced by construction in the channel-wall geometry
(CP2), not by a model-level proxy. `retention` is `Literal["channel"]` in v1 —
pave is a future value.

| Parameter                | Default | Sane range | Castability floor / note |
|---------------------------|---------|------------|--------------------------|
| `accent_stone_diameter`   | 1.5 mm  | 0.9 - 2.5 mm | channel wall thickness is a fixed construction margin, independent of this field |
| `accent_stone_height`     | 1.2 mm  | 0.8 - 3.0 mm | drives the accent bearing well depth |
| `accent_count_per_side`   | 3       | 1 - 8      | `side_stone_overcrowding` guards against the row overrunning the shoulder span before the ring base |
| `accent_gap`               | 0.3 mm  | 0.2 - 1.0 mm | edge-to-edge spacing along the shoulder; `side_stone_overcrowding` guards adjacent accents' true chord clearance (see docs/ringspec/contract.md) |
| `retention`                | channel | `channel`  | `Literal["channel"]`; pave is a future value |

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
