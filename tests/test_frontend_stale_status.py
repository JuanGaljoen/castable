"""Feedback about an input must not outlive that input's value (RNG-29).

Static JS-source contract, matching the scope note in tests/test_frontend.py:
the Flask test client runs no JavaScript, so the binding is asserted by reading
the script source and the live interaction is browser-QA'd. A source assertion
cannot prove the handler fires -- it proves the listener is wired and names the
elements it retires, which is the part that was simply absent.

The bug: photo.js bound a listener only on #estimate-btn, so "Choose a JPEG or
PNG photo first." survived choosing a JPEG, and #photo-detections asserted the
PREVIOUS photo's style over the newly chosen one. Found in RNG-23 browser QA,
where it cost real time -- a valid file was visible in the input while the page
insisted none had been chosen.
"""
from __future__ import annotations

import os
import re

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def _source(name: str) -> str:
    with open(os.path.join(REPO_ROOT, "static", name)) as fh:
        return fh.read()


# --- the photo status/detections are retired when the file input changes ----
def test_file_input_has_a_change_listener():
    src = _source("photo.js")
    assert re.search(
        r'\$\(\s*"ring-photo"\s*\)', src
    ), "photo.js never looks up #ring-photo outside onEstimate's files read"
    assert re.search(
        r'addEventListener\(\s*"change"', src
    ), "nothing in photo.js listens for a change on the file input"


def test_the_change_handler_clears_both_photo_feedback_elements():
    src = _source("photo.js")
    match = re.search(
        r"function clearPhotoFeedback\(\)\s*\{(.*?)\n  \}", src, re.DOTALL
    )
    assert match, "no clearPhotoFeedback() to bind to the change event"
    body = match.group(1)
    assert "setStatus" in body, "the stale status line is not cleared"
    assert "photo-detections" in body, (
        "the detections line still asserts the previous photo's style"
    )
    assert "hidden = true" in body, "#photo-detections is shown, never re-hidden"


def test_change_handler_leaves_field_markers_alone():
    # Deliberate: the low-confidence / adjusted markers caution about estimates
    # that are STILL IN THE FORM. Dropping the caution while its suspect value
    # stays is worse than a stale caution; applySpec clears both on the next
    # successful run.
    src = _source("photo.js")
    match = re.search(
        r"function clearPhotoFeedback\(\)\s*\{(.*?)\n  \}", src, re.DOTALL
    )
    assert match
    body = match.group(1)
    assert "clearLowConfidence" not in body and "clearAdjusted" not in body


# --- a generation error's field marker dies with the value it named ---------
def test_editing_a_flagged_field_clears_its_error_marker():
    # clearResult() already retires the banner AND the markers on the next
    # submit, so the residual staleness is narrow: the field stays red while
    # the user types the correction the message asked for.
    src = _source("app.js")
    assert re.search(
        r'addEventListener\(\s*"input"[^)]*\)', src
    ), "no input listener clears a field-error marker as the value changes"
    assert re.search(
        r'classList\.remove\("field-error"\).*?removeAttribute\("aria-invalid"\)',
        src,
        re.DOTALL,
    ), "the marker must be cleared for sighted AND assistive-tech users"
