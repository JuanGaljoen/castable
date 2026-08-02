# RNG-22 — Photo fidelity probe harness

**Branch:** `feature/rng-22-photo-fidelity-probe-harness`
**Type:** feature · **Status:** in flight

## Problem

Every fidelity ticket that follows (RNG-19, RNG-25, RNG-26, RNG-27) claims "the model
reads closer to the photo". Today the only way to judge that claim is to eyeball one
render at a time, by hand, through the browser. There is no repeatable run and no
before-picture to compare against.

The ad hoc script that investigated the deleted RNG-20 (`spikes/rng22/probe_vision.py`)
produced findings in one afternoon that 3400 unit tests had not: two of three photos had
oval centre stones we built round (-> RNG-23), one photo was rejected on format before
vision ran (-> RNG-28), and the castability failure RNG-20 assumed simply never occurred
(-> RNG-20 deleted). That signal should be reproducible on demand, not rediscovered.

## Success criteria

- [x] One documented command runs the whole corpus and prints a per-photo verdict plus a
      summary line.
- [x] Re-running after a geometry or vision change is one command, no editing.
- [x] Skips gracefully with a clear message when `ANTHROPIC_API_KEY` is absent; never
      fails the offline suite.
- [x] Corpus covers the supported archetypes plus a negative (non-ring) case — side-stone
      carried as an explicit declared gap (RNG-34).
- [x] Docs note explaining what it costs and when to run it.
- [x] Never collected by a normal `pytest` invocation.

**Verified 2026-08-01:** full suite 3443 passed (0:20:11), up from a 3426 baseline by the
17 new verdict tests. Live corpus run exercised end to end; findings below.

## Decisions (frozen in Understand)

| Question | Decision | Why |
|---|---|---|
| Failure bar | **Generation only.** A photo that should generate but doesn't = red. | Ticket-literal. Archetype mismatch is real signal but goes amber, not red, so an ambiguous photo can't make the harness cry wolf. File a bug if it fires. |
| Archetype mismatch | Reported prominently, never fatal | See above. |
| Artifacts | **Write STL + assembled spec per photo** to a gitignored dir | Human judgement of the output *is* the point (ticket, Out of Scope). The report answers "did it classify and generate"; the STL answers "does it look like the photo" — the question the whole fidelity block exists to move. Also avoids re-paying API cost just to look at what was already generated. |
| Transport | Flask **test client**, not real HTTP | Same code path the browser hits (magic-byte sniff -> vision -> `to_spec` -> `validate_spec` -> castability -> compose -> mesh validation) with no server to start and no port to own. |
| Fenced off from pytest | **Standalone script**, not a pytest marker | The repo has no pytest config, so a marker would need registering and could still be run by accident. A script the suite never collects is the stronger fence. |
| Corpus provenance | Commit the photos (user's call) | Noted for the record: `halo-oval.jpg` carries a visible GLAMIRA watermark — a retailer product shot. Flagged, decided, proceeding. |

## Corpus

Photos live at `probes/corpus/`, described by `manifest.json`. Adding a photo later is a
manifest entry plus a file — **no code change**.

| File | Expect | Notes |
|---|---|---|
| `solitaire-round.jpg` | `solitaire` | 4-prong, plain shank |
| `halo-oval.jpg` | `halo` | oval centre + pave shoulders — the RNG-24 evidence photo |
| `halo-round.png` | `halo` | round centre + pave shoulders; PNG exercises the other sniff branch |
| `trilogy-oval.jpg` | `trilogy` | oval centre, round sides; converted from WebP (RNG-28 still open) |
| `negative-puppies.jpg` | no ring | `ring_detected: false` is the pass condition |
| *(side-stone)* | `side_stone` | **MISSING** — declared in the manifest, reported as a gap. No photo available. |

Excluded deliberately: a personal portrait that was in the same source directory. A photo
of a person does not belong in a public repo, and the negative case is already covered.

## Design

```
probes/
  README.md            # what it costs, when to run, how to read the output
  fidelity_probe.py    # the harness
  corpus/
    manifest.json
    <the five photos>
  output/              # gitignored: <slug>.stl + <slug>.spec.json per photo
```

The harness splits into a **pure core** (testable offline, no key, no network) and a
**thin I/O shell** (the part that costs money):

- `load_manifest(path) -> list[Expectation]` — parse + validate the manifest, resolve
  photo paths, mark declared-but-absent entries as missing.
- `evaluate(expectation, record) -> Verdict` — pure. Maps what happened to
  `PASS` / `FAIL` / `MISMATCH` (amber) / `MISSING`. Holds the whole failure-bar decision
  in one function: only a ring photo that failed to classify or generate is `FAIL`; a
  negative photo passes iff `ring_detected` is false; an archetype difference is
  `MISMATCH` and does not colour the exit code.
- `probe(client, photo) -> Record` — the I/O shell, promoted from the spike: POST
  `/classify-ring`, then POST `/generate-ring` with the returned spec, capturing status,
  detected style, assembled spec, mesh headers and STL bytes.
- `main()` — key check and clean skip, run the corpus, write artifacts, print the table
  and summary, exit non-zero iff any `FAIL`.

The split is the point: the failure bar and the manifest semantics are the parts worth
testing, and they are exactly the parts that do not need an API key.

## Checkpoints

Per the repo rule, each is independently green and committable.

- [x] **CP1 — corpus + manifest + loader.** Commit the five photos, `manifest.json`, and
      `load_manifest` with its tests (schema, missing-entry handling, bad manifest).
- [x] **CP2 — verdict logic + reporting.** `evaluate`, `Verdict`, the summary/exit-code
      rule, and the rendered table. All pure, all tested offline. This is where the
      failure bar lives.
- [x] **CP3 — runner + artifacts + docs.** Wire `probe` to the real endpoints, write
      STL/spec artifacts, gitignore `probes/output/`, `probes/README.md` + README pointer,
      retire `spikes/rng22/`. Verify by running the real corpus once with a live key.

## What the first live run found (2026-08-01)

The harness paid for itself on its first run, which is the argument for it in one line.

```
FAIL  solitaire-round.jpg   no ring detected in a ring photo
ok    halo-oval.jpg         halo       watertight, no repair  55.7s
FAIL  halo-round.png        generate failed [400]: stone_exceeds_head
ok    trilogy-oval.jpg      trilogy    watertight, no repair  23.3s
gap   side-stone.jpg        no photo in the corpus for this entry
ok    negative-puppies.jpg  correctly declined to detect a ring

2/4 generated · 3 pass · 2 fail · 0 archetype mismatch · 1 corpus gap
```

1. **Vision is non-deterministic on an unambiguous photo.** `solitaire-round.jpg` came
   back `ring_detected: false` on the corpus run, then classified correctly ("Classic
   solitaire with four-prong cushion cut setting") on both re-runs. Same photo, same
   model, same prompt. Worth a ticket: a user who uploads a clear ring photo and is told
   "no ring detected" has no recourse but to try again, and nothing tells them to.

2. **A vision spec can still fail the casting gate — RNG-20's premise was not wrong, just
   under-sampled.** `halo-round.png` produced `stone_height: 5.2` against
   `setting_height: 3.0` and was rejected with `stone_exceeds_head`. RNG-20 was deleted on
   the evidence of 3/3 clean photos; the fourth photo breaks it. The estimates are
   internally inconsistent (a stone taller than the head that holds it), which is a
   *coherence* problem in the vision layer, not a castability floor being missed.

3. **A cut we can see but cannot express.** Vision read `solitaire-round.jpg` as a cushion
   cut — its own words — and wrote `shape: "round"`, because `Stones.shape` is
   `round | oval`. RNG-23 shipped oval and deferred the rest (-> RNG-33).

4. **Two harness bugs, both found by using it rather than testing it** — the RNG-23 lesson
   holding again. Ad hoc mode reported "expected None, vision read solitaire" as a
   mismatch, and a ring detected without an assembled spec was misreported as "no ring
   detected". Both fixed with tests.

Filed from this run: **RNG-31** (non-determinism), **RNG-32** (cross-field incoherence),
**RNG-33** (more cuts), **RNG-34** (the side-stone corpus gap).

## Second run, with the side-stone photo (2026-08-02)

```
ok    solitaire-round.jpg   solitaire  watertight, no repair  13.8s
ok    halo-oval.jpg         halo       watertight, no repair  41.1s
ok    halo-round.png        halo       watertight, no repair  35.6s
ok    trilogy-oval.jpg      trilogy    watertight, no repair  17.0s
warn  side-stone.jpg        solitaire  watertight, no repair  12.0s
ok    negative-puppies.jpg  correctly declined to detect a ring

5/5 generated · 5 pass · 0 fail · 1 archetype mismatch · 0 corpus gap
```

- **The corpus gap is closed; the archetype coverage is not.** Vision read an unambiguous
  side-stone ring (round centre, six prongs, shared-prong accents down both shoulders) as
  a **four-prong solitaire**, discarding the accents and the prong count. Adding the photo
  cannot fix that — the classifier will not select the archetype. So the `side_stone`
  geometry path is still never exercised from a photo. That is RNG-24 (the union forcing
  one reading) and RNG-26, not a corpus problem, and **RNG-34 should not be closed on this
  run alone.**
- **RNG-32 is intermittent, not systematic.** `halo-round.png` failed the casting gate on
  2026-08-01 and passed on 2026-08-02, same photo. Worse than a systematic bug: it cannot
  be caught by testing once.
- **The harness is only as repeatable as the layer it measures.** Vision wanders run to
  run, so a naive before/after compares two different specs. Geometry is deterministic
  given a spec; the recommended comparison for geometry/presentation work is to re-generate
  from the saved `<slug>.spec.json` rather than re-classify. Documented in
  `probes/README.md`.

Note the timings: 55.7s and 23.3s per photo, against the ~4s RNG-21 measured for classify
alone. The bulk is B-rep generation, not the API call.

## Tests

`tests/test_fidelity_probe.py` — offline, no key, no network, collected by the normal
suite (it tests the harness; it is not the harness).

- manifest: valid parse; unknown archetype rejected; declared-but-absent photo -> `MISSING`
- verdict: ring photo generated -> `PASS`; classify 4xx/5xx -> `FAIL`; generate 400
  (castability) -> `FAIL`; negative photo with `ring_detected: false` -> `PASS`; negative
  photo that *did* detect a ring -> `FAIL`; archetype differs -> `MISMATCH` and **exit
  code unaffected**
- summary: exit 0 when only `PASS`/`MISMATCH`/`MISSING`; exit 1 when any `FAIL`
- no-key path: clean skip message, exit 0

## Out of scope

Automated visual-similarity scoring (human judgement is the point). Running in CI.
Fixing RNG-28 (WebP) — the trilogy photo is converted instead.
