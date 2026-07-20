"""RNG-22 prototype: run real photos through the live upload -> generate path.

Written ad hoc to investigate RNG-20 (deleted: its premise, that vision specs
fail the casting gate, was disproved -- 3/3 real photos generated raw watertight).
Retained as the working prototype for RNG-22, which promotes it into a committed
harness with a real corpus.

Drives the real endpoints via the Flask test client, so it exercises exactly
what the browser hits: POST /classify-ring (magic-byte sniff, vision call,
to_spec) then POST /generate-ring with the returned spec (validate_spec ->
validate_castability -> compose -> mesh validation).

Makes real Anthropic API calls -- needs ANTHROPIC_API_KEY (.env is loaded by
create_app). One Haiku call per photo.

    python spikes/rng20/probe_vision.py ~/Desktop/solitaire.jpg ~/Desktop/halo.jpeg

Prints a per-photo verdict and exits non-zero if any photo failed to generate,
so re-running the corpus after a fix is one command.
"""
from __future__ import annotations

import io
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from ringcad.app import create_app  # noqa: E402


def probe(client, path: Path) -> dict:
    """Run one photo end to end. Returns a record of what each stage did."""
    rec: dict = {"photo": path.name, "stage": None, "ok": False}

    resp = client.post(
        "/classify-ring",
        data={"image": (io.BytesIO(path.read_bytes()), path.name)},
        content_type="multipart/form-data",
    )
    if resp.status_code != 200:
        rec["stage"] = "classify"
        rec["error"] = resp.get_json()
        rec["status"] = resp.status_code
        return rec

    body = resp.get_json()
    rec["detected_style"] = body.get("detected_style")
    rec["note"] = body.get("note")
    spec = body.get("spec")
    if not body.get("ring_detected") or spec is None:
        rec["stage"] = "classify"
        rec["error"] = "no ring detected"
        return rec

    rec["archetype"] = spec.get("archetype")
    rec["spec"] = spec
    rec["confidence"] = spec.get("confidence")

    gen = client.post("/generate-ring", json=spec)
    if gen.status_code != 200:
        rec["stage"] = "generate"
        rec["status"] = gen.status_code
        rec["error"] = gen.get_json()
        return rec

    rec["stage"] = "generate"
    rec["ok"] = True
    rec["mesh_valid"] = gen.headers.get("X-Mesh-Valid")
    rec["mesh_repaired"] = gen.headers.get("X-Mesh-Repaired")
    rec["repair_detail"] = gen.headers.get("X-Mesh-Repair-Detail")
    rec["stl_bytes"] = len(gen.data)
    return rec


def main(argv: list[str]) -> int:
    paths = [Path(a).expanduser() for a in argv]
    if not paths:
        print(__doc__)
        return 2

    client = create_app().test_client()
    records = []
    for path in paths:
        if not path.exists():
            print(f"!! {path} does not exist")
            continue
        print(f"-- {path.name} ...", flush=True)
        rec = probe(client, path)
        records.append(rec)
        print(json.dumps(rec, indent=2), flush=True)

    failed = [r for r in records if not r["ok"]]
    print(f"\n{len(records) - len(failed)}/{len(records)} generated")
    for rec in failed:
        print(f"  FAIL {rec['photo']} @ {rec['stage']}: {rec.get('error')}")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
