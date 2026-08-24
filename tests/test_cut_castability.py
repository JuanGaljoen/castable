"""The gate ASKS the cut profile (RNG-33 CP1).

docs/adr/0006's corollary: validation gates need the shape audit more urgently
than builders, because a wrong builder is visible and a wrong gate is silent.
RNG-23 left two gates measuring a circle of the SHORT axis:

  * `_min_prong_tip` divides `pi * stone_diameter` by the prong count, so on any
    elongated cut it under-reports the arc each prong gets and rejects specs the
    geometry can build -- the `_halo_overcrowding` bug of ADR-0006, second
    edition;
  * `_stone_curvature` re-derives `semi_minor / ratio` inline, an ellipse-only
    formula, while `outline.min_curvature_radius()` had no production caller.

Both now read `ringcad.ringspec.cuts`. Round must not move.
"""
from __future__ import annotations

import math

import pytest

from ringcad.ringspec import validate_spec
from ringcad.ringspec.castability import validate_castability
from ringcad.ringspec.cuts import profile_for


def _spec(shape="round", ratio=1.0, stone=6.5, prongs=4, **kw):
    return validate_spec({
        "archetype": "solitaire",
        "shank": {"inner_diameter": kw.get("bore", 17.0),
                  "band_width": 2.5, "band_thickness": 1.8},
        "setting": {"prong_count": prongs, "setting_height": 5.0},
        "stones": {"stone_diameter": stone, "stone_height": 4.0,
                   "shape": shape, "length_ratio": ratio},
        "motifs": [],
    })


def _codes(spec):
    return {v.code for v in validate_castability(spec)}


# --- the schema widened, without breaking anything --------------------------

@pytest.mark.parametrize("shape", [
    "round", "oval", "cushion", "emerald", "pear", "marquise"])
def test_every_cut_is_accepted_by_the_schema(shape):
    p = profile_for(shape)
    assert _spec(shape, p.default_ratio).stones.shape == shape


def test_a_spec_with_no_shape_still_means_round():
    spec = validate_spec({
        "archetype": "solitaire",
        "shank": {"inner_diameter": 17.0, "band_width": 2.5,
                  "band_thickness": 1.8},
        "setting": {"prong_count": 4, "setting_height": 5.0},
        "stones": {"stone_diameter": 6.5, "stone_height": 4.0},
        "motifs": [],
    })
    assert spec.stones.shape == "round"
    assert spec.stones.length_ratio == 1.0


def test_an_unbuildable_cut_is_rejected_naming_the_field():
    with pytest.raises(Exception, match="shape"):
        _spec("princess", 1.0)


# --- per-cut ratio: raised to the band, never silently left below -----------

@pytest.mark.parametrize("shape,expected", [
    ("emerald", 1.40), ("pear", 1.60), ("marquise", 1.95)])
def test_a_ratio_below_a_cuts_band_is_raised_to_that_cuts_default(
        shape, expected):
    """A marquise at 1.0 is a circle, not a marquise. Cuts whose band starts
    above 1.0 have no meaningful stone there, so filling it is a repair."""
    assert _spec(shape, 1.0).stones.length_ratio == pytest.approx(expected)


@pytest.mark.parametrize("shape", ["round", "oval", "cushion"])
def test_a_ratio_of_one_is_left_alone_where_it_is_legitimate(shape):
    """RNG-23's contract: an oval at ratio 1.0 IS a circle and stays one.
    A cushion at 1.00 is a square cushion, squarely inside its own band."""
    assert _spec(shape, 1.0).stones.length_ratio == 1.0


# --- _min_prong_tip now measures the real girdle ----------------------------

def test_round_prong_tip_arc_is_unchanged():
    """`perimeter` for a circle is exactly `pi * stone_diameter`, so the round
    gate keeps its pre-RNG-33 numbers to the bit."""
    p = profile_for("round")
    assert p.perimeter(6.5 / 2, 1.0) == pytest.approx(math.pi * 6.5)


def test_a_tiny_round_stone_still_trips_the_prong_tip_floor():
    assert "min_prong_tip" in _codes(_spec("round", 1.0, stone=1.0, prongs=6))


def test_an_elongated_cut_is_not_rejected_on_a_circles_arc():
    """The stone has more girdle than a circle of its short axis, so each prong
    gets more arc. Measuring the circle refused rings the geometry can build.

    The numbers, so the choice of 5.1mm is not a magic constant: at 6 prongs the
    tip floor needs a 5.348mm stone if the girdle is read as a circle, but a
    marquise at its conventional 1.95 carries 1.449x that girdle and clears the
    same floor at 4.921mm. 5.1mm sits between the two, which is the only band
    where the old rule and the new one disagree.

    **Was 4.5mm until RNG-33 CP3.** A marquise's two V-prongs FORK, so at 6
    prongs it now puts 8 tips on that girdle rather than 6, and the size at
    which it clears the floor rose by exactly that ratio -- 3.691 x 8/6 =
    4.921. The window narrowed; the principle did not move, which is why this
    test kept its name and its point.
    """
    between = 5.1
    assert "min_prong_tip" in _codes(
        _spec("round", 1.0, stone=between, prongs=6))
    assert "min_prong_tip" not in _codes(
        _spec("marquise", 1.95, stone=between, prongs=6))


# --- _stone_curvature asks, and only where the question applies -------------

def test_oval_curvature_violation_is_unchanged():
    codes = _codes(_spec("oval", 2.5, stone=2.0))
    assert "stone_curvature" in codes


def test_the_curvature_rule_does_not_fire_on_a_vertex_cut():
    """A vertex is not a tight curve: it cannot be swept along at ANY collar
    radius, which is why CP2 bores those seats instead (docs/adr/0008). Reading
    a vertex as infinite curvature would reject every cornered cut outright --
    the right answer to the wrong question."""
    for shape in ("emerald", "pear", "marquise"):
        p = profile_for(shape)
        assert "stone_curvature" not in _codes(_spec(shape, p.max_ratio,
                                                     stone=2.0))


def test_cushion_is_checked_because_its_girdle_is_smooth():
    assert profile_for("cushion").has_vertices is False
    tight = _spec("cushion", 1.30, stone=1.2)
    assert isinstance(_codes(tight), set)      # smoke: the rule runs at all


def test_the_curvature_violation_still_names_the_ratio_field():
    v = [x for x in validate_castability(_spec("oval", 2.5, stone=2.0))
         if x.code == "stone_curvature"]
    assert v and v[0].field == "stones.length_ratio"
