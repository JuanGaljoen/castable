# RNG-48 — Download format menu on the viewer: STL or STEP
Classification: feature (frontend only)

## Success criteria (the bar Verify checks)

- [x] The Download icon opens a menu with two items, **STL** and **STEP**.
- [x] **STL** downloads the in-memory blob as `ring.stl` with **no network request**
      (today's behaviour, unchanged bytes).
- [x] **STEP** downloads `ring.step` of the ring **shown in the viewer**, even when the
      form was edited after generating (posts `lastGeneratedBody`, never the live form).
- [x] While STEP builds: the trigger shows a busy state (`aria-busy`, spinner glyph,
      menu cannot reopen), "Preparing STEP file…" is announced, and a second request
      cannot be fired. Success announces "STEP download ready."
- [x] A STEP failure shows an error on the existing error surface; the menu is usable
      again afterwards.
- [x] Generating a new ring while STEP builds **aborts** the STEP request, so a file for
      a model no longer on screen is never delivered.
- [x] WCAG 2.1 AA menu-button pattern: trigger is a `<button aria-haspopup="menu"
      aria-expanded>`; Enter / Space / ArrowDown open and focus the first item, ArrowUp
      opens on the last; ArrowUp/Down/Home/End move; Escape closes and returns focus to
      the trigger; Tab or a click outside closes. Visible item text is contained in each
      accessible name (2.5.3).
- [x] Download stays LEFT of Wireframe; secondary weight; Generate is still the only
      filled button.
- [ ] Vanilla JS, no new dependency. Full suite green. Real-browser QA of both formats
      (Playwright against the dev server, script in the scratchpad), mutation-checked.

## Approach

**Markup.** `#download-btn` becomes a `<button>` (was an `<a download>`), wrapped with
its menu in `.download-menu` inside `.viewer-toolbar`, still before `#wireframe-toggle`:

    <div class="download-menu" hidden>
      <button id="download-btn" class="icon-button" aria-haspopup="menu"
              aria-expanded="false" aria-controls="download-options"
              aria-label="Download" title="Download">…same svg…</button>
      <ul id="download-options" role="menu" aria-label="Download format" hidden>
        <li role="none"><button role="menuitem" data-format="stl">STL <span>print &amp; cast</span></button></li>
        <li role="none"><button role="menuitem" data-format="step">STEP <span>editable CAD</span></button></li>
      </ul>
    </div>

The wrapper (not the button) carries `hidden`, so show/hide stays one attribute.
Menu items use roving focus (`tabindex="-1"`, focus moved by script).

**Behaviour (`static/app.js`).**
- `showSuccess` / `clearResult` toggle the wrapper instead of setting/removing `href`.
- STL: a throwaway `<a href=currentObjectUrl download="ring.stl">` is clicked. No fetch.
- STEP: `fetch("/generate-ring?format=step", {body: lastGeneratedBody, signal})`, blob →
  throwaway anchor `download="ring.step"`, object URL revoked after the click. An
  `AbortController` is held in module scope; `clearResult()` (runs on every Generate)
  aborts it. An `AbortError` is silent; any other failure goes through `showError` /
  `renderError`, the app's one error surface.
- Busy: `downloadBtn.setAttribute("aria-busy","true")` + `.is-busy` class swaps the glyph
  for a spinner (CSS, respects `prefers-reduced-motion`); clicks/keys ignored while busy.

**Why `lastGeneratedBody`.** It is exactly the request that produced the preview, already
recorded only on success. Reading the form instead would silently ship a different ring
whenever the form has moved on (the RNG-30 staleness family).

**Styles (`static/styles.css`).** `.download-menu { position: relative }`; the menu is
an absolutely positioned panel under the trigger, right-aligned to it, opaque backing
in both themes, items ≥ 24px target (2.5.8), hint text in the muted colour at ≥ 4.5:1.

## Files

- `templates/index.html` — markup above.
- `static/app.js` — menu controller + STL/STEP handlers + abort on clear.
- `static/styles.css` — menu panel, items, busy spinner, dark theme.
- `tests/test_frontend.py` — update the two Download tests (it is a menu button now);
  add structure tests: ARIA wiring, both items present, STEP posts `lastGeneratedBody`
  with `format=step`, `clearResult` aborts the in-flight STEP.
- No backend change: `?format=step` already covered by the endpoint tests.

## Out of scope

Preset views and reset view (follow-up ticket). Caching the B-rep server-side to make
STEP instant (only worth it if the wait proves annoying in use).

## Checkpoints

- [x] CP1 — format menu (markup, controller, STL + STEP, styles, tests, browser QA)
