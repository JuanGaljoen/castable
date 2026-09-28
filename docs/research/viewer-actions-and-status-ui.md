# Viewer actions and status UI — download button, status badge, success message

**Question:** after a successful `/generate-ring`, where should (1) the "Done —
download ready" text, (2) the castable-mesh status badge, and (3) the
"Download STL" button live — sidebar footer vs. floating over the 3D preview —
and how prominent should each be?

## a) Where does a primary export action live, and how prominent?

**Verdict: keep Download on the viewer, but demote it from a solid primary
button to a toolbar-style secondary/icon+label button, and put it in a
consistent toolbar position (trailing edge), not floating alone.**

- **Proximity wins over "put every button in the sidebar."** NN/g's core rule
  is that GUI elements placed too far from the object they act on get missed
  — their own example is an update button separated from the thing it updates
  by vertical distance, and users didn't see it. [Closeness of Actions and
  Objects in GUI Design (NN/g)](https://www.nngroup.com/articles/closeness-of-actions-and-objects-gui/).
  A "Download STL" button in the sidebar, three columns away from the model it
  exports, violates this; on the viewer it's correctly adjacent to its
  object. This is *why* moving it out of the sidebar footer was right.
- **But "on the viewer" doesn't mean "solid green and alone."** Apple's HIG
  toolbar guidance for document windows: the toolbar sits at the top of the
  content it acts on, and the **trailing end is the conventional slot for a
  whole-document action** (their own example is Pages' Share button living at
  the toolbar's trailing edge) — i.e., a small toolbar-weight control, not an
  oversized CTA. [Toolbars — Apple HIG](https://developer.apple.com/design/human-interface-guidelines/toolbars).
  Material 3's top-app-bar guidance is the same shape: frequent actions go in
  a toolbar, ordered by importance, not rendered as one large filled button
  competing with the content. [Top app bar guidelines — Material Design 3](https://m3.material.io/components/app-bars/guidelines).
- **One primary (filled) button per screen is the convention, and you likely
  already have one.** If "Generate" is the filled/primary button in the
  sidebar, a second filled button of equal visual weight ("Download STL",
  solid green) on the same screen splits attention and reads as two
  competing calls to action — this is the standard primary/secondary/ghost
  hierarchy convention (button-hierarchy sources agree there should be a
  single strongest CTA in view, with everything else visually subordinate).
  Concretely: **Download should be a secondary or outline/ghost button (or an
  icon button with a visible text label to satisfy 2.5.3, see (d)), sized
  like a toolbar action, sitting where the wireframe toggle already sits** —
  i.e. two toolbar-weight controls in the same visual register, not one loud
  button next to one quiet one.
- **Real product precedent, partially verified:** Onshape's own help docs
  confirm export is reached via a right-click/contextual "Export" action on
  the part or tab, not a large primary button — export is treated as a
  secondary, discoverable-but-not-shouted action even in a professional CAD
  tool. [Exporting Files — Onshape](https://cad.onshape.com/help/Content/File/exporting_files.htm).
  I could **not** verify Sketchfab's or the Three.js editor's exact download
  button styling/prominence from primary sources in this pass — search
  results for Sketchfab were inconsistent (viewer-overlay vs. below-viewer
  claims from secondary how-to sites, not Sketchfab's own docs) and the
  Three.js editor's live page couldn't be rendered by the fetch tool. Treat
  those two as **not verified**, not as supporting evidence.

## b) Where does result/validation status belong — badge on the object vs. near the trigger?

**Verdict: the mesh-validity badge belongs attached to the preview (the
object it describes), not the sidebar (the form that triggered it) — as an
overlay chip on/near the canvas, not sidebar text.**

- NN/g's indicator/validation/notification framework is explicit on this:
  **"indicators" are contextual, shown "in close proximity to that element"
  they describe** — and a castable/invalid mesh status is a property of the
  rendered model, not of the form. [Indicators, Validations, and
  Notifications — NN/G](https://www.nngroup.com/articles/indicators-validations-notifications/).
  A green "✓ Castable mesh" pill sitting in the sidebar, describing the thing
  rendered on the other side of the screen, is exactly the proximity failure
  NN/g's iTunes example illustrates in (a).
- Concretely: move the badge to a small chip **overlaid on the viewer**,
  e.g. near the "3D preview" heading (top-left) or beside the toolbar
  (top-right), not floating alone mid-canvas where it would obscure the
  model. Keep it non-colour-only per WCAG 1.4.1 (you already do this with
  ✓/⚠ glyphs — keep that).

## c) Is the redundant "Done — download ready" text message needed?

**Verdict: no — the visible state change (mesh renders, download button
becomes available/enabled) already satisfies "visibility of system status";
keep an announcement only as a screen-reader-only live region, drop the
visible sidebar line.**

- WCAG 4.1.3 (Status Messages) requires that a status be **programmatically
  available to assistive tech without requiring focus** — it does not require
  a *visible* success sentence. The mechanism is `role="status"` /
  `aria-live="polite"`, which can be applied to a visually-hidden element.
  [Understanding SC 4.1.3: Status Messages — W3C/WAI](https://www.w3.org/WAI/WCAG21/Understanding/status-messages.html).
  So: keep the aria-live region (you already have it) but make its visible
  text either removed or visually-hidden (`sr-only`) once the mesh badge and
  rendered preview are doing the visible job.
- GOV.UK's own guidance on notification/success banners: **use them
  sparingly, because evidence shows people miss banners**, and reserve them
  for confirming a completed action **when the user has a remaining task**
  ("Application submitted. Check your email...").
  [Notification banner — GOV.UK Design System](https://design-system.service.gov.uk/components/notification-banner).
  Here there's no remaining task — the model is already visible and the
  Download button is already live — so a persistent banner-style sentence is
  exactly the case GOV.UK says to avoid.
- NN/g's indicators/validations/notifications piece makes the same point from
  the other direction: a notification confirming something the user can
  already see happening (their example: adding to cart) is "less important to
  require the user to take action to acknowledge" — the state change itself
  is the feedback. [Indicators, Validations, and Notifications — NN/G](https://www.nngroup.com/articles/indicators-validations-notifications/).

## d) Grouping viewer controls into one toolbar — contrast, labels, overlay patterns

**Verdict: yes, group wireframe toggle + download + status badge into one
consistent toolbar register on the viewer (not scattered corners), and treat
every one of them as a real UI component for contrast/labelling purposes —
overlaying on a canvas does not relax WCAG, it makes the contrast check
harder because the backdrop is a rendered photo/mesh, not a flat colour.**

- **Non-text contrast (1.4.11):** any control boundary, icon, or focus
  indicator overlaid on the canvas needs **3:1 contrast against its
  immediately adjacent colour(s)**, and because the canvas background is a
  live-rendered (dark, but variable) 3D scene rather than a fixed colour,
  this is the one that will actually break in testing — give every overlay
  control its own solid/translucent backing chip rather than relying on
  "dark canvas + light icon" contrast that a bright rotated ring face could
  defeat. [Non-Text Contrast — Deque University summary of WCAG 2.1 1.4.11](https://dequeuniversity.com/resources/wcag2.1/1.4.11-non-text-contrast).
- **Text contrast (1.4.3)** still applies separately to any label text in the
  chip (e.g. "Wireframe", "Download STL") — 4.5:1 for normal-size text, same
  variable-background caveat.
- **Icon-only buttons need an accessible name, and if any visible text is
  present it must be included verbatim in that name (2.5.3 Label in
  Name).** If you keep "Download STL" as icon+text (recommended per (a), also
  the more robust accessibility choice — an icon-only download control would
  need `aria-label="Download STL"` matching exactly), you satisfy this by
  construction; an icon-only glyph with a *different* internal label (e.g.
  icon labelled "Export" while showing a download glyph) would fail 2.5.3
  even though it has *some* accessible name. [Understanding SC 2.5.3: Label
  in Name — W3C](https://w3c.github.io/wcag21/understanding/label-in-name.html).
- **Toolbar grouping precedent:** Material 3's top-app-bar spec explicitly
  recommends collecting the current page's frequent actions into one
  ordered toolbar (most-used action leftmost/first) rather than scattering
  individual buttons around the screen, with overflow for anything beyond
  the primary set. [Top app bar guidelines — Material Design 3](https://m3.material.io/components/app-bars/guidelines).
  Apple's HIG toolbar page makes the same recommendation for document
  windows specifically: put the commands people use on *this* document in
  one toolbar strip, trailing-edge for the most important/whole-document
  action. [Toolbars — Apple HIG](https://developer.apple.com/design/human-interface-guidelines/toolbars).

## Recommended concrete layout

- **Viewer toolbar** (top-right, replacing the lone green Download button):
  a single small toolbar/chip cluster — `[Wireframe]  [↓ Download STL]` — both
  rendered as **secondary/outline weight**, same visual register, each with
  a solid backing chip for contrast against the dark canvas, "Download STL"
  keeping its visible text (not icon-only) to sidestep 2.5.3 entirely.
- **Viewer status chip** (top-left, beside or under the "3D preview"
  heading): the castable/invalid badge, unchanged content (✓/⚠ + text),
  moved here instead of the sidebar — it now sits next to the thing it
  describes.
- **Sidebar footer:** drop the visible "Done — download ready." sentence.
  Keep an `aria-live="polite"` region for it (WCAG 4.1.3 compliance), but
  make it visually hidden (`sr-only`) — the rendered model + status chip +
  now-usable Download button already carry the visible signal.
- **Generate button** stays the sidebar's one filled/primary button —
  restoring a single primary CTA on screen instead of two.

## Where I looked / what I could not verify

- **Verified from primary/first-party sources:** NN/g (*Closeness of
  Actions and Objects*, *Indicators, Validations, and Notifications*),
  W3C/WAI (*Understanding 4.1.3*, *Understanding 2.5.3*, 1.4.11 summarised via
  Deque University's WCAG resource page), GOV.UK Design System (*Notification
  banner*), Apple HIG (*Toolbars*), Material Design 3 (*Top app bar
  guidelines*), Onshape's own help docs (*Exporting Files*).
- **Not found / not verified in this pass:** Sketchfab's own design docs for
  its viewer toolbar (only third-party how-to pages turned up, and they
  disagree with each other on button position — do not cite them as
  Sketchfab's actual layout); the Three.js editor's live toolbar layout (the
  fetch tool could not render the page; would need a manual screenshot or the
  editor's own source in `github.com/mrdoob/three.js/tree/dev/editor`);
  Carbon, Atlassian Design System (Atlaskit), and Shopify Polaris were not
  consulted this pass — if a future pass wants a fourth/fifth design-system
  citation for the toolbar-grouping point, `carbondesignsystem.com`'s
  Toolbar component and Polaris's `ActionList`/`Page` header actions pattern
  are the pages to start with.
- **GOV.UK / WCAG guidance above is settled** (primary sources agree, no
  contradiction found). The **prominence recommendation in (a)** is
  contested only in the sense that no single source states "download button
  must be secondary-weight" as a rule — that's this note's synthesis of the
  one-primary-button convention plus Apple/Material toolbar precedent, not a
  verbatim citation; flagged here as inference, not fact.
