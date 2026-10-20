# RNG-29 — Photo error message does not clear when a file is chosen

**Type:** fix · **Landed:** 2026-09-16 · *Written after the fact from the project
record; there was no frozen design.*

## Problem

The status line under "Estimate from photo" outlived the condition it described: it
said "Choose a JPEG or PNG photo first." while a valid JPEG sat visibly in the input.
Cosmetic in code, genuinely misleading in use: it cost real time in RNG-23 QA, where
element ids and script syntax were checked before anyone realised the message was
simply stale.

## Outcome

**Shipped: the feedback-lifetime rule.** Feedback about an input must not outlive that
input's value, but "feedback" splits two ways. *Claims about the file* (the status
line, `#photo-detections`) die with the file, because they assert something no longer
true. *Cautions about values* (the amber low-confidence and indigo adjusted markers)
survive, because the values they caution about are still in the form; dropping a
caution while its suspect value stays is worse than a stale caution. `applySpec`
already clears those on the next successful run, when the values change too.

- **A second instance the ticket never reported.** `showDetections` un-hid
  `#photo-detections` and nothing re-hid it, so choosing a different photo left
  "Detected: oval solitaire" asserting the *previous* photo's style. Found by applying
  the rule to every element in the panel rather than only the one in the report.
- **The generate side was checked, and was already nearly right.** `clearResult()`
  retires both the banner and the field markers on every submit. The residual: the
  field stayed red while the user typed the correction the message asked for. Fixed
  for the marker only; the banner carries the instruction being followed ("must be at
  least 0.8mm") and must survive the keystrokes that satisfy it. A state indicator dies
  with the value; an instruction does not.

**What surprised us: how it was proved.** The house style for frontend work is Python
source inspection (`tests/test_frontend_*.py`), which for a DOM-event bug can only show
the listener is *wired*, never that it *fires*, so the four new tests say so in their
own docstring and are not the evidence. The evidence is a browser, and it needed no new
dependency: `playwright` is already in the venv, and
`p.chromium.launch(channel="chrome")` drives the system Chrome with no browser
download, against the real dev server. The script lived in the scratchpad, so
`requirements.txt` and `tests/test_requirements.py` were untouched. Then the QA script
itself was mutation-tested: `git stash push` the fix, rerun, `git stash pop`; four
target checks went red and three deliberate controls stayed green.

Committing the harness properly (declaring playwright, owning browser setup in CI) was
judged a real ticket, not a rider on a Low paper cut; it is RING-44 in Orbit.

**ADRs it left.** docs/adr/0017 (mutation-test a QA script against the broken code),
written later from this ticket.
