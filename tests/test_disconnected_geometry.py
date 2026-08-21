"""Disconnected geometry is refused, not shipped (RNG-33 CP2).

A mesh in PIECES is not "an invalid mesh you might still want to download". It
is not one object: it cannot be cast, and `validate_and_repair` already calls
that case not auto-repairable. Handing it back with `X-Mesh-Valid: false` gives
the user an STL that looks downloadable and fails in the slicer.

**Why this is checked on the artifact rather than gated from the spec.** The one
combination that reaches it -- a channel side-stone band with an elongated centre
stone (RNG-39) -- fails in a SCATTER across `length_ratio`, not in a region:

    marquise  1.50:OK  1.70:XX  1.90:OK  2.10:XX  2.30:OK  2.50:OK

A threshold rule would reject working rings and admit broken ones while looking
principled, which is exactly the drift docs/adr/0002 was written about. Measuring
what was actually built cannot drift, and stops firing by itself once RNG-39
lands. It is also deliberately NARROWER than "not castable": a thin wall or an
open edge still ships, preserving the documented behaviour that download works
regardless of validation status.
"""
from __future__ import annotations

import json

import pytest

from ringcad.app import create_app
from ringcad.mesh_validator import RepairOutcome


@pytest.fixture
def client():
    app = create_app()
    app.config.update(TESTING=True)
    return app.test_client()


def _body(**stones):
    group = {"stone_diameter": 6.5, "stone_height": 4.0}
    group.update(stones)
    return {
        "archetype": "solitaire",
        "shank": {"inner_diameter": 17.0, "band_width": 2.5,
                  "band_thickness": 1.8},
        "setting": {"prong_count": 4, "setting_height": 5.0},
        "stones": group,
        "motifs": [],
    }


# --- the validator carries the count structurally --------------------------

def test_repair_outcome_reports_the_body_count():
    """Carried as a field, not only inside the display `detail` string, so the
    endpoint can act on it without parsing prose."""
    assert RepairOutcome(True, False, "", b"", 1).body_count == 1
    assert RepairOutcome(False, True, "3 disjoint bodies, not auto-repairable",
                         b"", 3).body_count == 3


def test_body_count_defaults_to_one_for_existing_callers():
    assert RepairOutcome(True, False, "", b"").body_count == 1


# --- the endpoint refuses a mesh in pieces ---------------------------------

def test_a_mesh_in_pieces_is_refused_with_400(client, monkeypatch):
    monkeypatch.setattr(
        "ringcad.app.validate_and_repair",
        lambda raw: RepairOutcome(
            False, True, "3 disjoint bodies, not auto-repairable", raw, 3),
    )
    resp = client.post("/generate-ring", json=_body())
    assert resp.status_code == 400
    payload = json.loads(resp.data)
    assert "disconnected" in payload["error"].lower()
    assert "3 separate pieces" in payload["detail"]


def test_the_refusal_says_what_to_change(client, monkeypatch):
    """The user cannot act on 'not a manifold'. They can act on 'try a
    different centre stone shape or ring style'."""
    monkeypatch.setattr(
        "ringcad.app.validate_and_repair",
        lambda raw: RepairOutcome(False, True, "2 disjoint bodies", raw, 2),
    )
    payload = json.loads(client.post("/generate-ring", json=_body()).data)
    assert "shape" in payload["detail"] or "style" in payload["detail"]


# --- everything else still ships, exactly as documented --------------------

def test_an_invalid_but_connected_mesh_still_downloads(client, monkeypatch):
    """CLAUDE.md: "Download works regardless of validation status." A thin wall
    or an open edge is still one object and still ships with the header telling
    the truth. Only a mesh in PIECES is refused."""
    monkeypatch.setattr(
        "ringcad.app.validate_and_repair",
        lambda raw: RepairOutcome(
            False, True, "mesh not watertight after repair", raw, 1),
    )
    resp = client.post("/generate-ring", json=_body())
    assert resp.status_code == 200
    assert resp.headers["X-Mesh-Valid"] == "false"


def test_a_healthy_mesh_is_unaffected(client):
    resp = client.post("/generate-ring", json=_body())
    assert resp.status_code == 200
    assert resp.headers["X-Mesh-Valid"] == "true"
    assert resp.headers["X-Mesh-Repaired"] == "false"


@pytest.mark.parametrize("shape,ratio", [
    ("cushion", 1.02), ("emerald", 1.40), ("pear", 1.60), ("marquise", 1.95)])
def test_every_new_cut_generates_through_the_real_endpoint(
        client, shape, ratio):
    """The real path, not the kernel directly. RNG-23's lesson: the DEFAULT ring
    style silently discarded the chosen shape because it took the legacy flat-7
    request path, and a fully green 3413-test suite never noticed."""
    resp = client.post("/generate-ring",
                       json=_body(shape=shape, length_ratio=ratio))
    assert resp.status_code == 200, resp.data[:400]
    assert resp.headers["X-Mesh-Valid"] == "true"
    assert resp.headers["X-Mesh-Repaired"] == "false"
