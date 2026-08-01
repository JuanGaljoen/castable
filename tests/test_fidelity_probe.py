"""RNG-22: offline tests for the photo fidelity probe harness.

These test the harness, they are not the harness -- no API key, no network, no
Anthropic calls. The probe itself (`probes/fidelity_probe.py`) is a standalone
script that pytest never collects; only its pure core is exercised here.
"""
import json

import pytest

from probes.fidelity_probe import (
    CORPUS_DIR,
    Expectation,
    ManifestError,
    Verdict,
    load_manifest,
)


def write_manifest(tmp_path, photos):
    path = tmp_path / "manifest.json"
    path.write_text(json.dumps({"photos": photos}))
    return path


def touch(tmp_path, name):
    (tmp_path / name).write_bytes(b"\xff\xd8\xff\xe0not-really-a-jpeg")


# --- manifest loading ------------------------------------------------------


def test_loads_a_ring_entry(tmp_path):
    touch(tmp_path, "a.jpg")
    path = write_manifest(
        tmp_path,
        [{"file": "a.jpg", "expect_ring": True, "expected_archetype": "halo"}],
    )

    (exp,) = load_manifest(path)

    assert exp.file == "a.jpg"
    assert exp.expect_ring is True
    assert exp.expected_archetype == "halo"
    assert exp.path == tmp_path / "a.jpg"
    assert exp.present is True


def test_loads_a_negative_entry(tmp_path):
    touch(tmp_path, "n.jpg")
    path = write_manifest(
        tmp_path,
        [{"file": "n.jpg", "expect_ring": False, "expected_archetype": None}],
    )

    (exp,) = load_manifest(path)

    assert exp.expect_ring is False
    assert exp.expected_archetype is None


def test_declared_but_absent_photo_is_a_gap_not_an_error(tmp_path):
    path = write_manifest(
        tmp_path,
        [
            {
                "file": "side-stone.jpg",
                "expect_ring": True,
                "expected_archetype": "side_stone",
            }
        ],
    )

    (exp,) = load_manifest(path)

    assert exp.present is False


def test_unknown_archetype_is_rejected(tmp_path):
    touch(tmp_path, "a.jpg")
    path = write_manifest(
        tmp_path,
        [{"file": "a.jpg", "expect_ring": True, "expected_archetype": "tiara"}],
    )

    with pytest.raises(ManifestError, match="tiara"):
        load_manifest(path)


def test_ring_entry_without_an_archetype_is_rejected(tmp_path):
    touch(tmp_path, "a.jpg")
    path = write_manifest(
        tmp_path,
        [{"file": "a.jpg", "expect_ring": True, "expected_archetype": None}],
    )

    with pytest.raises(ManifestError, match="expected_archetype"):
        load_manifest(path)


def test_missing_manifest_file_is_reported_clearly(tmp_path):
    with pytest.raises(ManifestError, match="not found"):
        load_manifest(tmp_path / "nope.json")


def test_malformed_manifest_is_reported_clearly(tmp_path):
    path = tmp_path / "manifest.json"
    path.write_text("{not json")

    with pytest.raises(ManifestError):
        load_manifest(path)


def test_entry_without_a_file_is_rejected(tmp_path):
    path = write_manifest(tmp_path, [{"expect_ring": True}])

    with pytest.raises(ManifestError, match="file"):
        load_manifest(path)


# --- the committed corpus itself -------------------------------------------


def test_the_committed_corpus_loads():
    """The real manifest parses and every non-gap photo is actually there."""
    expectations = load_manifest(CORPUS_DIR / "manifest.json")

    assert len(expectations) >= 5
    by_name = {e.file: e for e in expectations}
    assert by_name["negative-puppies.jpg"].expect_ring is False
    assert by_name["solitaire-round.jpg"].expected_archetype == "solitaire"


def test_the_committed_corpus_covers_the_archetypes_and_a_negative():
    expectations = load_manifest(CORPUS_DIR / "manifest.json")

    covered = {e.expected_archetype for e in expectations if e.expect_ring}
    assert {"solitaire", "halo", "trilogy", "side_stone"} <= covered
    assert any(not e.expect_ring for e in expectations)


def test_every_ring_photo_in_the_corpus_is_a_supported_upload_format():
    """RNG-28: the endpoint sniffs magic bytes and accepts JPEG/PNG only."""
    for exp in load_manifest(CORPUS_DIR / "manifest.json"):
        if not exp.present:
            continue
        head = exp.path.read_bytes()[:8]
        assert head.startswith(b"\xff\xd8\xff") or head.startswith(
            b"\x89PNG\r\n\x1a\n"
        ), f"{exp.file} is neither JPEG nor PNG and would be rejected"


def test_verdict_values_are_distinct():
    assert len({v.value for v in Verdict}) == len(list(Verdict))


def test_expectation_slug_is_filesystem_safe():
    exp = Expectation(
        file="halo-oval.jpg",
        expect_ring=True,
        expected_archetype="halo",
        note="",
        path=CORPUS_DIR / "halo-oval.jpg",
    )
    assert exp.slug == "halo-oval"
