"""RNG-22: the failure bar, tested offline.

`evaluate` is the whole pass/fail decision in one pure function, so the rule the
harness enforces can be pinned down without a key, a network, or a photo.
"""
import tempfile
from pathlib import Path

from probes.fidelity_probe import (
    Expectation,
    Record,
    Verdict,
    evaluate,
    exit_code,
)

# A photo that genuinely exists on disk: `present` is a filesystem fact, and an
# entry with no file behind it is a declared gap that short-circuits to MISSING.
_PRESENT = Path(tempfile.mkdtemp()) / "present.jpg"
_PRESENT.write_bytes(b"\xff\xd8\xff\xe0")


def ring(archetype="solitaire", file="a.jpg"):
    return Expectation(
        file=file,
        expect_ring=True,
        expected_archetype=archetype,
        note="",
        path=_PRESENT,
    )


def negative(file="n.jpg"):
    return Expectation(
        file=file,
        expect_ring=False,
        expected_archetype=None,
        note="",
        path=_PRESENT,
    )


def generated(archetype="solitaire"):
    return Record(
        stage="generate",
        generated=True,
        ring_detected=True,
        archetype=archetype,
        mesh_valid="true",
        mesh_repaired="false",
    )


# --- ring photos -----------------------------------------------------------


def test_ring_photo_that_generates_passes():
    assert evaluate(ring(), generated()).verdict is Verdict.PASS


def test_ring_photo_that_fails_classification_fails():
    rec = Record(stage="classify", generated=False, status=502, error="upstream")

    assert evaluate(ring(), rec).verdict is Verdict.FAIL


def test_ring_photo_rejected_before_vision_fails():
    """RNG-28's WebP rejection looked like this: a 400 on the magic-byte sniff."""
    rec = Record(stage="classify", generated=False, status=400, error="format")

    assert evaluate(ring(), rec).verdict is Verdict.FAIL


def test_ring_photo_that_fails_the_casting_gate_fails():
    rec = Record(
        stage="generate",
        generated=False,
        ring_detected=True,
        archetype="halo",
        status=400,
        error="prong_count too high for stone_diameter",
    )

    assert evaluate(ring("halo"), rec).verdict is Verdict.FAIL


def test_ring_photo_where_no_ring_was_detected_fails():
    rec = Record(stage="classify", generated=False, ring_detected=False)

    assert evaluate(ring(), rec).verdict is Verdict.FAIL


# --- archetype mismatch is amber, never red --------------------------------


def test_wrong_archetype_that_still_generates_is_a_mismatch():
    result = evaluate(ring("halo"), generated("solitaire"))

    assert result.verdict is Verdict.MISMATCH
    assert "halo" in result.detail and "solitaire" in result.detail


def test_a_mismatch_does_not_fail_the_run():
    results = [evaluate(ring("halo"), generated("solitaire"))]

    assert exit_code(results) == 0


def test_an_ad_hoc_photo_has_nothing_to_mismatch_against():
    """A one-off path has no expected archetype; anything it builds is a pass."""
    ad_hoc = Expectation(
        file="whatever.jpg",
        expect_ring=True,
        expected_archetype=None,
        note="ad hoc",
        path=_PRESENT,
    )

    assert evaluate(ad_hoc, generated("halo")).verdict is Verdict.PASS


def test_a_mismatch_that_also_failed_to_generate_is_a_failure():
    """Generation is the bar; a mismatch never downgrades a real failure."""
    rec = Record(
        stage="generate",
        generated=False,
        ring_detected=True,
        archetype="solitaire",
        status=400,
    )

    assert evaluate(ring("halo"), rec).verdict is Verdict.FAIL


# --- the negative case -----------------------------------------------------


def test_negative_photo_passes_when_no_ring_is_detected():
    rec = Record(stage="classify", generated=False, ring_detected=False)

    assert evaluate(negative(), rec).verdict is Verdict.PASS


def test_negative_photo_fails_when_a_ring_is_hallucinated():
    assert evaluate(negative(), generated()).verdict is Verdict.FAIL


# --- declared gaps ---------------------------------------------------------


def test_absent_photo_is_missing_not_failed(tmp_path):
    gap = Expectation(
        file="side-stone.jpg",
        expect_ring=True,
        expected_archetype="side_stone",
        note="",
        path=tmp_path / "side-stone.jpg",
    )

    assert evaluate(gap, None).verdict is Verdict.MISSING


def test_a_gap_does_not_fail_the_run(tmp_path):
    gap = Expectation(
        file="side-stone.jpg",
        expect_ring=True,
        expected_archetype="side_stone",
        note="",
        path=tmp_path / "side-stone.jpg",
    )

    assert exit_code([evaluate(gap, None)]) == 0


# --- the exit code ---------------------------------------------------------


def test_all_passing_exits_zero():
    assert exit_code([evaluate(ring(), generated())]) == 0


def test_any_failure_exits_non_zero():
    bad = evaluate(ring(), Record(stage="classify", generated=False, status=502))
    good = evaluate(ring(), generated())

    assert exit_code([good, bad, good]) == 1


def test_no_results_exits_zero():
    assert exit_code([]) == 0


# --- the no-key path -------------------------------------------------------


def test_without_a_key_it_skips_cleanly_and_exits_zero(monkeypatch, capsys):
    """It must never fail a run just because the machine has no key."""
    import types

    from probes import fidelity_probe

    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    # A local .env would otherwise supply one; neutralise the lookup.
    monkeypatch.setitem(
        __import__("sys").modules,
        "dotenv",
        types.SimpleNamespace(load_dotenv=lambda *a, **k: None),
    )

    code = fidelity_probe.main([])

    assert code == 0
    out = capsys.readouterr().out
    assert "SKIPPED" in out
    assert "ANTHROPIC_API_KEY" in out
