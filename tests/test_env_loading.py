"""RNG-21: `.env` is loaded at app startup.

The README tells users to put ANTHROPIC_API_KEY in a local `.env`, but nothing
loaded it -- a `.env` had no effect on its own. `create_app()` now calls
`load_dotenv()` so a `.env` populates the process environment.

TEST SEAM: `create_app` binds `from dotenv import load_dotenv` into the
ringcad.app namespace, so we monkeypatch `ringcad.app.load_dotenv` (where it is
LOOKED UP). NO filesystem `.env` is written; we assert the wiring, not python-
dotenv's own behaviour. Explicit env exports still win because load_dotenv does
not override existing vars by default -- an invariant we do not re-test here.
"""
from ringcad.app import create_app


def test_create_app_loads_dotenv(monkeypatch):
    calls = []
    monkeypatch.setattr("ringcad.app.load_dotenv", lambda *a, **k: calls.append(1))
    create_app()
    assert calls, "create_app() should call load_dotenv() at startup"
