# 0008 — We render metal only, so model the NEGATIVE, not the setting

**Date:** 2026-08-06
**Status:** Accepted
**Context:** RNG-19 CP3 (channel setting) and CP4 (halo plate)

## What happened

Two archetypes were built as *assemblies of setting parts* and both read as
parametric rather than as jewelry, for the same underlying reason.

- **Channel (RNG-11)** placed an `accent_seat` — a `Torus` collar deliberately
  left proud of the band — at every stone, retained by two `Torus` rails sitting
  ON the surface. Channel setting has **no prongs and no per-stone collar at
  all**; that is its definition. It was halo geometry used where its premise did
  not hold, and it produced a row of raised donuts.
- **Halo (RNG-9)** built the body as N `accent_seat` collars welded by a gallery
  rail. On the corpus halo that is a **0.7–0.8mm tube around a 1.2mm stone** —
  metal two thirds the stone's own diameter — and `collar_tr` is pinned at
  `max(MIN_WALL/2, 0.35)`, so **no tuning could make it finer.** It read as
  lumpy tubing.

Both were fixed by inverting the construction: **build the metal solid, then cut
the stones out of it.**

## Why this is the right default here

We never render gemstones (out of scope per RNG-27), so every model is metal
alone, and *a setting is the negative of its stones*. Modelling the setting as
positive parts means every retaining feature is sized by its own floor —
independently, and each at the casting minimum — so the metal accumulates into
tubes and collars that no parameter can slim. Cutting instead makes the
remaining metal **whatever the bores leave**, which is governed by the real
geometry rather than by a sum of minima.

It also pays off structurally. ADR-0007's tessellation cracking came from fusing
near-tangent bodies; **a cut has no tangency to crack along**, and a cut cannot
open a solid unless it severs it — which a floor rule can forbid outright. In
both checkpoints the subtractive version was the one that held the RNG-17 bar.

The bearings come free. A channel's wall seats fall out of cutting each stone at
its full diameter across a narrower trench (it bites `GIRDLE_PENETRATION` into
either wall); a halo's seats are simply the bores. Neither is modelled as a
feature, so neither has to be built at the 0.25mm scale that has bitten us twice.

## The rule

> **When the model is metal-only, prefer subtraction to assembly.** Build the
> body the setting is cut from, then remove the stones. Reach for positive parts
> only for metal that genuinely stands proud — a claw, a bead.

## The trap that comes with it

Subtraction has its own silent failure, and we hit it: a bore that does not
**open** becomes a sealed internal void. The first halo seats left a 0.02mm floor
underneath, sealing 15 cavities — and the result reported **watertight, one B-rep
solid, every casting floor met**, because nothing was missing, only enclosed.
`.solids()` cannot see it and neither can `is_watertight`.

**Assert mesh BODY COUNT on any subtractive module.** That is the check that
catches it, and it is the sibling of ADR-0005's "assert volume, not just
watertightness".

Two further findings worth carrying:

- **Cut once, with every tool.** `compose` subtracted iteratively and raised
  `Null TopoDS_Shape` on a 13-accent halo; a single `cut(*tools)` resolved it.
  This is ADR-0001's single-general-fuse lesson applied to subtraction.
- **Measure a tapered wall where it is thinnest in the STRUCTURE, not at the
  surface.** The metal between two tapered bores is a V-shaped ridge — near zero
  at the top, thickening with depth. Gating on the top sliver forced 1.1mm of
  flat plate between halo stones and looked wrong; real halos set stones nearly
  touching with a bright-cut edge. The load-bearing section is the one lower
  down. (Stated plainly because this rule *loosened* after a visual complaint,
  which is the shape of a mistake — the defence is that the original measurement
  was wrong for a tapered feature, corroborated by `docs/reference/halo.png`.)

## How the defects were found at all

Not by the suite — it was green through every one of them. They were found by
**comparing a render against a trade reference sketch**
(`docs/reference/halo.png`). Both fixes came from one person saying "that is not
what this is supposed to look like."

The reference is a **semi-mount**: bare metal, empty prongs, no stones — exactly
our rendering situation. That matters beyond the shape, because it retired an
excuse. `docs/jewelry-design-principles.md` §"The metal-only caveat" warns that a
correct model can look odd without its stones, and that reasoning had already
been used to defer this work out of RNG-19 as unjudgeable before RNG-27. A
semi-mount sketch is bare metal too and reads unmistakably as jewelry. **Where a
semi-mount reference exists, the caveat does not apply — compare against it.**
