"""RNG-22: run a corpus of real ring photos through the live upload -> generate
path and report what came out.

This is the measuring stick for the fidelity block. Every ticket after RNG-23
claims "the model reads closer to the photo"; this is how that claim gets
checked -- same photos, same command, before and after.

It does NOT judge the likeness. It runs the real path, reports what happened at
each stage, and saves the geometry so a human can look at it. Human judgement of
the output is the point.

    python probes/fidelity_probe.py                 # the committed corpus
    python probes/fidelity_probe.py ~/photo.jpg     # ad hoc, one-off

Costs real Anthropic API calls -- one per photo. Needs ANTHROPIC_API_KEY (a
local .env is loaded by create_app). Skips cleanly with a message when absent.
"""
from __future__ import annotations

import argparse
import io
import json
import os
import sys
import time
import typing
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

CORPUS_DIR = Path(__file__).resolve().parent / "corpus"
OUTPUT_DIR = Path(__file__).resolve().parent / "output"


class ManifestError(Exception):
    """The corpus manifest is missing, malformed, or describes something we
    cannot check (an archetype the schema does not define, say)."""


class Verdict(Enum):
    """What the harness concluded about one photo.

    Only FAIL colours the exit code. MISMATCH is real signal -- vision picked a
    different archetype than the corpus says the photo is -- but a genuinely
    ambiguous photo must not make the harness cry wolf, so it stays amber.
    """

    PASS = "PASS"
    FAIL = "FAIL"
    MISMATCH = "MISMATCH"
    MISSING = "MISSING"


@dataclass(frozen=True)
class Expectation:
    """One manifest entry: a photo and what the corpus says it is."""

    file: str
    expect_ring: bool
    expected_archetype: str | None
    note: str
    path: Path

    @property
    def present(self) -> bool:
        """False for a declared gap -- an entry with no photo behind it yet."""
        return self.path.is_file()

    @property
    def slug(self) -> str:
        """Filesystem-safe stem, used to name this photo's saved artifacts."""
        return Path(self.file).stem


@dataclass
class Record:
    """What actually happened when one photo went through the real path."""

    stage: str
    generated: bool
    ring_detected: bool | None = None
    archetype: str | None = None
    detected_style: str | None = None
    note: str | None = None
    spec: dict | None = None
    status: int | None = None
    error: object = None
    mesh_valid: str | None = None
    mesh_repaired: str | None = None
    repair_detail: str | None = None
    stl_bytes: int = 0
    seconds: float = 0.0
    stl: bytes = field(default=b"", repr=False)


@dataclass(frozen=True)
class Result:
    """An expectation, what happened, and the verdict that follows."""

    expectation: Expectation
    record: Record | None
    verdict: Verdict
    detail: str

    @property
    def file(self) -> str:
        return self.expectation.file


def evaluate(expectation: Expectation, record: Record | None) -> Result:
    """Decide one photo's verdict. Pure -- this is the whole failure bar.

    The rule, in order of precedence:

    * no photo behind a declared entry -> MISSING (a known gap, not a failure)
    * a negative photo passes exactly when no ring was detected
    * a ring photo must classify AND generate; anything short of that is FAIL
    * only then, a differing archetype is MISMATCH -- amber, never red, because
      a genuinely ambiguous photo must not make the harness cry wolf
    """

    def result(verdict: Verdict, detail: str = "") -> Result:
        return Result(expectation, record, verdict, detail)

    if not expectation.present:
        return result(Verdict.MISSING, "no photo in the corpus for this entry")

    if record is None:
        return result(Verdict.MISSING, "photo was not run")

    if not expectation.expect_ring:
        if record.ring_detected:
            return result(
                Verdict.FAIL,
                f"a ring was detected in a non-ring photo "
                f"(as {record.archetype or record.detected_style})",
            )
        return result(Verdict.PASS, "correctly declined to detect a ring")

    if record.ring_detected is False:
        return result(Verdict.FAIL, "no ring detected in a ring photo")

    if not record.generated:
        where = record.stage
        why = record.error if record.error is not None else "unknown"
        status = f" [{record.status}]" if record.status else ""
        return result(Verdict.FAIL, f"{where} failed{status}: {why}")

    if (
        expectation.expected_archetype is not None
        and record.archetype != expectation.expected_archetype
    ):
        return result(
            Verdict.MISMATCH,
            f"expected {expectation.expected_archetype}, "
            f"vision read {record.archetype}",
        )

    return result(Verdict.PASS, "")


def exit_code(results: list[Result]) -> int:
    """Non-zero iff something genuinely failed. Gaps and mismatches don't count."""
    return 1 if any(r.verdict is Verdict.FAIL for r in results) else 0


def supported_archetypes() -> set[str]:
    """Read the archetype tags off the RingSpec union.

    Derived rather than hardcoded so a new archetype needs no edit here.
    """
    from ringcad.ringspec.models import RingSpec

    (union,) = typing.get_args(RingSpec)[:1]  # strip the Annotated wrapper
    return {
        member.model_fields["archetype"].default
        for member in typing.get_args(union)
    }


def probe(client, photo: Path) -> Record:
    """Run one photo through the real endpoints and record what happened.

    Deliberately the same two calls the browser makes -- POST /classify-ring
    then POST /generate-ring with the spec that came back -- so the magic-byte
    sniff, the vision call, spec assembly, validation, the casting gate, the
    compose and the mesh check are all genuinely in the path. Calling
    `classify_ring()` directly would skip most of that; RNG-23 shipped three
    bugs that a fully green suite missed for exactly that reason.
    """
    started = time.monotonic()

    resp = client.post(
        "/classify-ring",
        data={"image": (io.BytesIO(photo.read_bytes()), photo.name)},
        content_type="multipart/form-data",
    )
    if resp.status_code != 200:
        return Record(
            stage="classify",
            generated=False,
            status=resp.status_code,
            error=resp.get_json(),
            seconds=time.monotonic() - started,
        )

    body = resp.get_json()
    spec = body.get("spec")
    if not body.get("ring_detected"):
        return Record(
            stage="classify",
            generated=False,
            ring_detected=False,
            detected_style=body.get("detected_style"),
            note=body.get("note"),
            seconds=time.monotonic() - started,
        )
    if spec is None:
        # A ring *was* seen but no spec came back -- a different failure from
        # "not a ring", and worth saying so rather than blaming the photo.
        return Record(
            stage="classify",
            generated=False,
            ring_detected=True,
            detected_style=body.get("detected_style"),
            note=body.get("note"),
            error="a ring was detected but no spec was assembled",
            seconds=time.monotonic() - started,
        )

    gen = client.post("/generate-ring", json=spec)
    if gen.status_code != 200:
        return Record(
            stage="generate",
            generated=False,
            ring_detected=True,
            archetype=spec.get("archetype"),
            detected_style=body.get("detected_style"),
            note=body.get("note"),
            spec=spec,
            status=gen.status_code,
            error=gen.get_json(),
            seconds=time.monotonic() - started,
        )

    return Record(
        stage="generate",
        generated=True,
        ring_detected=True,
        archetype=spec.get("archetype"),
        detected_style=body.get("detected_style"),
        note=body.get("note"),
        spec=spec,
        mesh_valid=gen.headers.get("X-Mesh-Valid"),
        mesh_repaired=gen.headers.get("X-Mesh-Repaired"),
        repair_detail=gen.headers.get("X-Mesh-Repair-Detail"),
        stl_bytes=len(gen.data),
        seconds=time.monotonic() - started,
        stl=gen.data,
    )


def save_artifacts(expectation: Expectation, record: Record, out: Path) -> None:
    """Write this photo's geometry and spec so a human can look at them.

    The report says whether it classified and generated; only the geometry
    answers "does it look like the photo". Keeping it also means a re-run after
    a change has something to be compared *against* -- and that the API call
    already paid for does not have to be paid for twice just to see the result.
    """
    out.mkdir(parents=True, exist_ok=True)
    if record.spec is not None:
        (out / f"{expectation.slug}.spec.json").write_text(
            json.dumps(record.spec, indent=2)
        )
    if record.stl:
        (out / f"{expectation.slug}.stl").write_bytes(record.stl)


def load_manifest(path: Path) -> list[Expectation]:
    """Parse the corpus manifest into expectations, validating as we go.

    A declared entry whose photo is absent is a *gap*, not an error: the corpus
    can name a ring style we have no license-clean photo for yet, and the run
    reports it as an explicit hole rather than quietly having one fewer photo.
    """
    path = Path(path)
    if not path.is_file():
        raise ManifestError(f"corpus manifest not found: {path}")

    try:
        data = json.loads(path.read_text())
    except json.JSONDecodeError as exc:
        raise ManifestError(f"corpus manifest is not valid JSON: {exc}") from exc

    entries = data.get("photos")
    if not isinstance(entries, list):
        raise ManifestError("corpus manifest needs a 'photos' list")

    known = supported_archetypes()
    expectations = []
    for index, entry in enumerate(entries):
        if not isinstance(entry, dict):
            raise ManifestError(f"photo entry {index} is not an object")

        file = entry.get("file")
        if not file:
            raise ManifestError(f"photo entry {index} has no 'file'")

        expect_ring = bool(entry.get("expect_ring", True))
        archetype = entry.get("expected_archetype")

        if expect_ring and not archetype:
            raise ManifestError(
                f"{file}: a ring photo needs an 'expected_archetype'"
            )
        if archetype is not None and archetype not in known:
            raise ManifestError(
                f"{file}: unknown archetype {archetype!r} "
                f"(known: {', '.join(sorted(known))})"
            )

        expectations.append(
            Expectation(
                file=file,
                expect_ring=expect_ring,
                expected_archetype=archetype,
                note=entry.get("note", ""),
                path=path.parent / file,
            )
        )

    return expectations


MARKS = {
    Verdict.PASS: "ok  ",
    Verdict.FAIL: "FAIL",
    Verdict.MISMATCH: "warn",
    Verdict.MISSING: "gap ",
}


def format_row(result: Result) -> str:
    """One photo, one line."""
    rec = result.record
    parts = [f"{MARKS[result.verdict]}  {result.file:<24}"]

    if rec is not None and rec.generated:
        mesh = "watertight" if rec.mesh_valid == "true" else "NOT WATERTIGHT"
        if rec.mesh_repaired == "true":
            mesh += f" (REPAIRED: {rec.repair_detail or 'unspecified'})"
        else:
            mesh += ", no repair"
        parts.append(f"{rec.archetype:<10} {mesh}  {rec.seconds:.1f}s")
    elif rec is not None:
        parts.append(result.detail)
    else:
        parts.append(result.detail)

    if result.verdict is Verdict.MISMATCH:
        parts.append(f"<- {result.detail}")

    return "  ".join(parts)


def report(results: list[Result], out: Path | None) -> None:
    """Print the per-photo verdicts and the summary line."""
    print()
    for result in results:
        print(format_row(result))

    counts = {v: sum(1 for r in results if r.verdict is v) for v in Verdict}
    ran = [r for r in results if r.verdict is not Verdict.MISSING]
    generated = sum(
        1 for r in ran if r.record is not None and r.record.generated
    )
    expected_to_generate = sum(1 for r in ran if r.expectation.expect_ring)

    print()
    summary = (
        f"{generated}/{expected_to_generate} generated · "
        f"{counts[Verdict.PASS]} pass · {counts[Verdict.FAIL]} fail · "
        f"{counts[Verdict.MISMATCH]} archetype mismatch · "
        f"{counts[Verdict.MISSING]} corpus gap"
    )
    print(summary)

    for result in results:
        if result.verdict is Verdict.FAIL:
            print(f"  FAIL {result.file}: {result.detail}")
        if result.verdict is Verdict.MISSING:
            print(f"  gap  {result.file}: {result.detail}")

    if out is not None and generated:
        print(f"\nGeometry written to {out} — open it next to the photos.")


def run(expectations: list[Expectation], out: Path | None) -> list[Result]:
    """Run every present photo, saving artifacts as we go."""
    from ringcad.app import create_app

    client = create_app().test_client()
    results = []

    for expectation in expectations:
        if not expectation.present:
            results.append(evaluate(expectation, None))
            continue

        print(f"-- {expectation.file} ...", flush=True)
        record = probe(client, expectation.path)
        if out is not None:
            save_artifacts(expectation, record, out)
        results.append(evaluate(expectation, record))

    return results


def ad_hoc_expectations(paths: list[str]) -> list[Expectation]:
    """Treat bare paths as ring photos with no archetype expectation.

    Useful for a one-off look at a photo that isn't in the corpus; every
    archetype reads as a mismatch-free PASS because there is nothing to compare
    against.
    """
    expectations = []
    for raw in paths:
        path = Path(raw).expanduser().resolve()
        expectations.append(
            Expectation(
                file=path.name,
                expect_ring=True,
                expected_archetype=None,
                note="ad hoc",
                path=path,
            )
        )
    return expectations


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Run ring photos through the live classify -> generate path and "
            "report what came out. Costs one Anthropic call per photo."
        )
    )
    parser.add_argument(
        "photos",
        nargs="*",
        help="ad hoc photo paths; defaults to the committed corpus",
    )
    parser.add_argument(
        "--manifest",
        default=str(CORPUS_DIR / "manifest.json"),
        help="corpus manifest (default: the committed corpus)",
    )
    parser.add_argument(
        "--output",
        default=str(OUTPUT_DIR),
        help="where to write generated STL + spec (default: probes/output)",
    )
    parser.add_argument(
        "--no-artifacts",
        action="store_true",
        help="do not save geometry; print the report only",
    )
    args = parser.parse_args(argv)

    if not os.environ.get("ANTHROPIC_API_KEY"):
        # A local .env is loaded by create_app, so consult it before giving up.
        try:
            from dotenv import load_dotenv

            load_dotenv()
        except ImportError:
            pass

    if not os.environ.get("ANTHROPIC_API_KEY"):
        print(
            "SKIPPED: the fidelity probe needs a real ANTHROPIC_API_KEY.\n"
            "It calls the live vision API once per photo (~$0.003 each).\n"
            "Set it in the environment or in a local .env, then re-run."
        )
        return 0

    try:
        if args.photos:
            expectations = ad_hoc_expectations(args.photos)
        else:
            expectations = load_manifest(Path(args.manifest))
    except ManifestError as exc:
        print(f"ERROR: {exc}")
        return 2

    out = None if args.no_artifacts else Path(args.output)
    results = run(expectations, out)
    report(results, out)
    return exit_code(results)


if __name__ == "__main__":
    raise SystemExit(main())
