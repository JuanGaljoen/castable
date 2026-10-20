# RING-4: 3D preview keeps stale geometry after the form changes

Type: fix. Formerly RNG-30.

## Problem

After a generate, editing any field (or a photo prefill) leaves the old model
in the viewer, presented as current. `syncGenerateEnabled` already knows the
form no longer matches `lastGeneratedBody` (it re-enables Generate), but it
never touches the viewer.

## Decision

Keep the model visible but de-emphasised, so the before/after comparison
survives:

- the canvas dims (`#viewer-canvas.is-stale`), and still orbits;
- quiet inline text beside the "3D preview" heading:
  "Out of date — generate to update" (`#viewer-stale`, `role="status"`),
  glyph + text, never colour alone.

Stale means: a model is on screen (`lastGeneratedBody !== null`) and the form
would post a different body. It is derived in `syncGenerateEnabled` from the
same comparison that disables Generate, so the two can never disagree. It
follows that editing a value back clears it, a failed generate leaves it set,
and a successful generate clears it.

## Success criteria

- [x] Any change to a field that feeds the request, including the photo
      prefill, dims the model and shows the note.
- [x] A successful generate clears both; editing back to the shown values
      clears both; a failed generate leaves them.
- [x] No note and no dimming before the first generate.
- [x] WCAG 2.1 AA: the note meets text contrast, is announced once per
      transition, and does not rely on colour.

## Checkpoints

- [x] CP1: stale cue wired through `syncGenerateEnabled`, source tests +
      browser QA (mutation-tested).

## Outcome

Shipped as one checkpoint: `#viewer-stale` beside the heading plus
`#viewer-canvas.is-stale`, both set in `syncGenerateEnabled`.

- **Opacity was the wrong dim.** The first cut faded the canvas with
  `opacity: 0.4`. Source tests and the browser script both passed, but the
  light-theme screenshot showed the page bleeding through: the stage went grey,
  the ring read brighter, and the note lost contrast. Only looking at the
  render caught it. `filter: brightness(0.45)` darkens the canvas's own stage
  in either theme.
- **Browser QA** (outside the repo, per the zero-install pattern): 10 checks
  covering field edits, edit-back, a forced 400, a real photo prefill
  (`halo-oval.jpg`), 1440x900 no-scroll and mobile. Mutation-tested: 4 of 10
  fail on the pre-fix `app.js`.
- **Filed:** RING-45, Chrome's native "No file chosen" tooltip on the photo
  input, spotted during review. Pre-existing and unrelated to staleness.
