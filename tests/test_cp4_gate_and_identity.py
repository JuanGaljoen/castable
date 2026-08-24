"""RNG-33 CP4 — the gate counts TIPS, and repair may not change what a cut IS.

Two defects that only exist because CP3 landed, plus the identity rule the
frozen spec asked for.

**The gate counted prongs.** `_min_prong_tip` divides the girdle perimeter by
`setting.prong_count` to get the arc each prong may occupy. After CP3 a V-prong
FORKS: an emerald at four prongs puts eight arms on the girdle, a marquise at six
puts eight. Counting placements rather than tips under-reports crowding on every
cornered or pointed cut -- the ADR-0006 pattern in a third gate, and the reason
that ADR says a wrong gate is more urgent than a wrong builder: a wrong builder
is visible and a wrong gate is silent.

**Repair could change a cut's identity.** `coherence.py` repairs
`stone_curvature` by scaling `stones.length_ratio` inversely, clamped only to the
schema's 1.0-2.5. A marquise at 1.95 could therefore be "repaired" to 1.05 and
handed back still labelled `marquise`, rendering as a lens. Repair may change a
thing's DIMENSIONS; it must not silently change what it is.
"""
from __future__ import annotations

import pytest

from ringcad.ringspec import validate_spec
from ringcad.ringspec.castability import validate_castability
from ringcad.ringspec.coherence import make_coherent
from ringcad.ringspec.cuts import ProngType, profile_for


def _spec(shape="round", ratio=None, stone=6.5, prongs=4):
    p = profile_for(shape)
    return validate_spec({
        "archetype": "solitaire",
        "shank": {"inner_diameter": 17.0, "band_width": 2.5,
                  "band_thickness": 1.8},
        "setting": {"prong_count": prongs, "setting_height": 5.0},
        "stones": {"stone_diameter": stone, "stone_height": 4.0,
                   "shape": shape,
                   "length_ratio": p.default_ratio if ratio is None else ratio},
        "motifs": [],
    })


def _codes(spec):
    return {v.code for v in validate_castability(spec)}


def _tips(shape, n):
    layout = profile_for(shape).prong_layout(n)
    return len(layout) + sum(1 for _, k in layout if k is ProngType.V)


# --- the gate counts tips ---------------------------------------------------

@pytest.mark.parametrize("shape,n,expected", [
    ("round", 4, 4), ("round", 6, 6),      # nothing forks
    ("oval", 4, 4), ("cushion", 4, 4),     # rounded corners take claws
    ("emerald", 4, 8), ("emerald", 6, 10),  # four cut corners, four forks
    ("pear", 4, 5), ("pear", 6, 7),        # one point
    ("marquise", 4, 6), ("marquise", 6, 8),  # two points
])
def test_a_fork_puts_two_tips_on_the_girdle(shape, n, expected):
    assert _tips(shape, n) == expected


def test_a_small_emerald_is_refused_because_eight_arms_do_not_fit():
    """4mm across, four V-prongs: eight arms sharing that girdle, each derived
    at 0.556mm against a 0.7mm floor. Counting four placements instead put it
    at 1.112mm and let it through."""
    assert "min_prong_tip" in _codes(_spec("emerald", stone=4.0, prongs=4))


def test_the_same_emerald_at_a_workable_size_still_passes():
    """The rule has to bite on the crowded case WITHOUT rejecting the sizes a
    jeweller actually sets, or it is just a smaller stone limit."""
    assert "min_prong_tip" not in _codes(_spec("emerald", stone=6.5, prongs=4))


@pytest.mark.parametrize("shape", ["round", "oval", "cushion"])
@pytest.mark.parametrize("stone,prongs", [(4.0, 4), (6.5, 4), (6.5, 6), (9.0, 6)])
def test_cuts_with_nothing_to_fork_are_completely_unmoved(shape, stone, prongs):
    """No V, so tips == prongs and the arithmetic is character-for-character
    what it was. Round must not move, as ever."""
    ratio = 1.5 if shape == "oval" else None
    before = _tips(shape, prongs)
    assert before == prongs
    assert ("min_prong_tip" in _codes(_spec(shape, ratio=ratio, stone=stone,
                                            prongs=prongs))) == (
        stone == 4.0 and prongs == 6)


# --- identity: a cut's ratio stays inside the cut's own band ----------------
#
# The frozen spec expected the threat here to be REPAIR: `coherence.py` scales
# `stones.length_ratio` down for a `stone_curvature` violation, so a marquise at
# 1.95 could in principle be repaired to 1.05 and handed back still labelled
# marquise, rendering as a lens.
#
# That threat is not reachable, and the test below proves why rather than
# asserting it: CP1's `_stone_curvature` returns early for any cut that
# `has_vertices`, because a vertex cannot be followed by a swept collar at ANY
# radius and asking the question would reject every cornered cut outright. So it
# cannot fire on emerald, pear or marquise. Measured by fuzzing 7500 in-band
# specs: repair moves the ratio 12 times and NEVER out of band.
#
# The real hole was on the INPUT side, and nothing was watching it.

@pytest.mark.parametrize("shape", ["cushion", "emerald", "pear", "marquise"])
def test_stone_curvature_cannot_fire_on_a_cut_with_vertices(shape):
    """The reason the spec's repair guard is unreachable, pinned so that
    re-enabling curvature for a cornered cut re-opens the question loudly."""
    p = profile_for(shape)
    if not p.has_vertices:
        pytest.skip("cushion's corners are rounded; the question does apply")
    # Small and elongated: the tightest curvature this cut can be asked for.
    spec = _spec(shape, ratio=p.max_ratio, stone=1.9)
    assert "stone_curvature" not in _codes(spec)


@pytest.mark.parametrize("shape,given,expected", [
    # ABOVE the band -> clamped to the ceiling. This half did not exist before
    # CP4, so a "cushion" at 2.38 built and was called a cushion.
    ("cushion", 2.38, 1.3),
    ("emerald", 2.0, 1.75),
    ("pear", 2.5, 2.1),
    # BELOW the band -> filled with the cut's conventional default (CP1).
    ("marquise", 1.0, 1.95),
    ("pear", 1.0, 1.6),
    # Inside the band, and the bands that legitimately reach the schema edges,
    # are left exactly alone.
    ("cushion", 1.02, 1.02),
    ("marquise", 2.5, 2.5),
    ("oval", 2.5, 2.5),
])
def test_the_ratio_is_held_inside_its_cuts_band_at_both_ends(shape, given, expected):
    assert _spec(shape, ratio=given).stones.length_ratio == pytest.approx(expected)


def test_an_oval_at_two_point_five_is_still_untouched():
    """RNG-39's known-limitation case rides on this exact value, and oval's
    band is the full 1.0-2.5, so the new ceiling must not catch it."""
    assert _spec("oval", ratio=2.5).stones.length_ratio == 2.5


@pytest.mark.parametrize("shape", ["oval", "cushion", "emerald", "pear", "marquise"])
def test_repair_never_moves_a_ratio_outside_its_own_cuts_band(shape):
    """A property, swept rather than spot-checked, because the failure it
    guards against is a value drifting a little further on each of six repair
    passes -- which no single example would show."""
    import random
    rng = random.Random(f"cp4-{shape}")
    p = profile_for(shape)
    for _ in range(60):
        spec = _spec(shape,
                     ratio=round(rng.uniform(p.min_ratio, p.max_ratio), 3),
                     stone=round(rng.uniform(1.5, 10.0), 2),
                     prongs=rng.choice([4, 6]))
        repaired, _ = make_coherent(spec.model_dump(), {})
        got = repaired["stones"]["length_ratio"]
        assert p.min_ratio - 1e-9 <= got <= p.max_ratio + 1e-9, (
            f"{shape} repaired to {got}, outside [{p.min_ratio}, {p.max_ratio}]")


@pytest.mark.parametrize("shape", ["cushion", "emerald", "pear", "marquise"])
def test_repair_never_changes_the_cut_itself(shape):
    """Repair may change a thing's DIMENSIONS; it must not change what it is.
    The shape field is not a repair target at all, and this says so."""
    spec = _spec(shape, ratio=profile_for(shape).max_ratio, stone=1.9)
    repaired, _ = make_coherent(spec.model_dump(), {})
    assert repaired["stones"]["shape"] == shape
