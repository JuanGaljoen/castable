"""The preview says so when the form no longer matches the model on screen.

Static source contract, as in tests/test_frontend_stale_status.py: the Flask
test client runs no JavaScript, so these prove the cue exists and is driven
from the same comparison that disables Generate. Whether it fires is
browser-QA'd.

The bug: editing the form (or a photo prefill) left the previous model in the
viewer presented as current, and a stale round solitaire was twice mistaken
for a freshly generated oval during browser QA.
"""
from __future__ import annotations

import os
import re

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _read(*parts: str) -> str:
    with open(os.path.join(REPO_ROOT, *parts)) as fh:
        return fh.read()


def _sync_fn() -> str:
    js = _read("static", "app.js")
    fn = re.search(r"function syncGenerateEnabled\(\)\s*\{.*?\n\}", js, re.S)
    assert fn, "no syncGenerateEnabled()"
    return fn.group(0)


def test_stale_note_sits_beside_the_heading_hidden_by_default():
    html = _read("templates", "index.html")
    title = re.search(r'<div class="viewer-title">(.*?)</div>', html, re.S)
    assert title, "no .viewer-title"
    note = re.search(r'<p[^>]*id="viewer-stale"[^>]*>(.*?)</p>', title.group(1), re.S)
    assert note, "#viewer-stale is not beside the 3D preview heading"
    tag = note.group(0)
    assert 'role="status"' in tag
    assert re.search(r"\bhidden\b", tag), "the note must start hidden"
    assert "generate to update" in note.group(1).lower()


def test_staleness_is_derived_from_the_generate_comparison():
    """One comparison drives both, so Generate and the cue never disagree."""
    fn = _sync_fn()
    assert re.search(r"viewerStaleEl\.hidden\s*=\s*!stale", fn)
    assert re.search(r'classList\.toggle\(\s*"is-stale"\s*,\s*stale\s*\)', fn)
    # A model must be on screen: nothing is stale before the first generate.
    assert re.search(r"stale\s*=\s*lastGeneratedBody\s*!==\s*null\s*&&\s*!unchanged", fn)


def test_the_photo_prefill_reaches_the_stale_check():
    js = _read("static", "app.js")
    assert re.search(
        r'addEventListener\(\s*"ring:spec-applied"\s*,\s*syncGenerateEnabled\s*\)', js
    )


def test_stale_canvas_is_dimmed_and_the_note_carries_a_glyph():
    css = _read("static", "styles.css")
    rule = re.search(r"#viewer-canvas\.is-stale\s*\{([^}]*)\}", css)
    assert rule and "brightness(" in rule.group(1), "a stale canvas is not dimmed"
    # Opacity lets the page show through: on the light theme the dark stage
    # washes out grey and the ring reads brighter, not dimmer.
    assert "opacity" not in rule.group(1)
    assert re.search(r"\.viewer-stale::before\s*\{[^}]*content", css), (
        "the note relies on colour alone"
    )
