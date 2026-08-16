"""The adjusted-for-castability marker on the form (RNG-32 CP3).

Static structure + JS source contract, matching the scope note in
tests/test_frontend.py: the Flask test client runs no JavaScript, so behaviour
is asserted by reading the script source for the contract it must implement,
and the live interaction is browser-QA'd.

Without this, RNG-32's coherence repair silently rewrites numbers the user
was just shown -- breaking the "estimates only, verify before generating"
promise the photo flow makes just as surely as an unflagged low-confidence
estimate would.
"""
from __future__ import annotations

import os

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _source(name: str) -> str:
    with open(os.path.join(REPO_ROOT, "static", name)) as fh:
        return fh.read()


# --- the marker is distinct from low-confidence, not just recoloured --------
def test_adjusted_marker_is_a_separate_class_from_low_confidence():
    src = _source("photo.js")
    assert "adjusted-for-castability" in src
    assert "low-confidence" in src
    assert "flagAdjusted" in src and "flagLowConfidence" in src


def test_adjusted_css_differs_by_more_than_colour():
    # WCAG 2.1 AA 1.4.1: colour alone must not be the only distinguishing
    # signal between the two caution states.
    css = _source("styles.css")
    assert "adjusted-for-castability" in css
    assert "border-style: dashed" in css


# --- adjustments are read from the API response and applied to the form ----
def test_handle_success_reads_adjustments_from_the_response():
    src = _source("photo.js")
    assert "data.adjustments" in src


def test_apply_spec_flags_every_adjustment_by_its_bare_field_name():
    src = _source("photo.js")
    # adjustment.field is a dotted RingSpec path ("stones.stone_height");
    # the marker must key off the LAST segment, matching the input id
    # convention `conf` already relies on for low-confidence.
    assert "adjustment.field" in src
    assert 'split(".")' in src


# --- a re-run clears stale markers, mirroring clearLowConfidence -----------
def test_a_new_estimate_run_clears_stale_adjustment_markers():
    src = _source("photo.js")
    assert "function clearAdjusted" in src
    assert "clearAdjusted()" in src


# --- announced, not just shown: aria-live picks up the summary -------------
def test_photo_status_is_a_live_region():
    with open(os.path.join(REPO_ROOT, "templates", "index.html")) as fh:
        html = fh.read()
    assert 'id="photo-status"' in html
    assert 'aria-live="polite"' in html
