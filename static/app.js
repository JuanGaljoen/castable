// RNG-3 — Ring parameter form controller (vanilla JS, no libraries).
// Gathers the 7 params, POSTs to /generate-ring, wires the result UI.
// Module-scoped blob/objectUrl are retained for RNG-4 (viewer) reuse.
"use strict";

const NUMBER_KEYS = [
  "inner_diameter",
  "band_width",
  "band_thickness",
  "stone_diameter",
  "stone_height",
  "setting_height",
];

// Composable features (RNG-24): any subset, not a choice of one archetype.
// Keyed by feature name; `group` is the spec key, `fieldset` the revealed
// <fieldset> id, `numberKeys`/`intKeys`/`stringKeys` the group's inputs
// (numbers via Number, ints via parseInt, strings read verbatim — e.g. a
// <select> value). A registry, not an if-chain, so a new feature is one
// entry (RNG-10 CP3, widened RNG-24).
//
// Nothing in the form OFFERS a feature. The photo is the only thing that
// puts one on the ring: upload, and whatever it detected appears, filled in.
// A feature can be removed (vision is not always right), but there is no
// "add" — this is a tool for reproducing a ring you photographed, not a
// configurator for assembling one from parts.
const FEATURES = {
  halo: {
    group: "halo",
    fieldset: "halo-fields",
    numberKeys: ["halo_stone_diameter", "halo_gap", "halo_stone_height"],
    intKeys: ["halo_stone_count"],
    stringKeys: [],
  },
  trilogy: {
    group: "trilogy",
    fieldset: "trilogy-fields",
    numberKeys: ["side_stone_diameter", "side_stone_height", "side_stone_gap"],
    intKeys: [],
    stringKeys: [],
  },
  side_stone: {
    group: "side_stone",
    fieldset: "side-stone-fields",
    numberKeys: ["accent_stone_diameter", "accent_stone_height", "accent_gap"],
    intKeys: ["accent_count_per_side"],
    stringKeys: ["retention"],
  },
};

// Every feature-group field id (for required-toggling and error clearing).
const FEATURE_FIELD_KEYS = Object.values(FEATURES).flatMap(
  (cfg) => cfg.numberKeys.concat(cfg.intKeys, cfg.stringKeys)
);

// The fieldset's own visibility IS the state — no parallel flag to drift
// out of step with what the user can actually see and edit.
function isFeatureActive(name) {
  const fieldset = document.getElementById(FEATURES[name].fieldset);
  return !!(fieldset && !fieldset.hidden);
}

function activeFeatures() {
  return Object.keys(FEATURES).filter(isFeatureActive);
}

const form = document.getElementById("ring-form");
const generateBtn = document.getElementById("generate-btn");
const statusEl = document.getElementById("status");
const errorEl = document.getElementById("error");
const errorMessageEl = document.getElementById("error-message");
const stderrDetails = document.getElementById("stderr-details");
const stderrText = document.getElementById("stderr-text");
const downloadBtn = document.getElementById("download-btn");
const meshStatusEl = document.getElementById("mesh-status");

// Retained across generations; the viewer (RNG-4) will read these.
let currentBlob = null;
let currentObjectUrl = null;

// Structured RingSpec JSON (RNG-9 CP4, widened RNG-24): shared shank/setting/
// stones plus a group for EVERY active feature — any subset, not one
// archetype's worth. A plain centre stone sends the shared groups alone; the
// schema forbids extra keys, so an absent feature's group is never attached.
function gatherStructuredBody() {
  const body = {
    shank: {
      inner_diameter: Number(document.getElementById("inner_diameter").value),
      band_width: Number(document.getElementById("band_width").value),
      band_thickness: Number(document.getElementById("band_thickness").value),
      outer_profile: document.getElementById("outer_profile").value,
      inner_profile: document.getElementById("inner_profile").value,
    },
    setting: {
      prong_count: parseInt(document.getElementById("prong_count").value, 10),
      setting_height: Number(document.getElementById("setting_height").value),
    },
    stones: {
      stone_diameter: Number(document.getElementById("stone_diameter").value),
      stone_height: Number(document.getElementById("stone_height").value),
      ...stoneShapeFields(),
    },
  };
  for (const name of activeFeatures()) {
    const cfg = FEATURES[name];
    const group = {};
    for (const key of cfg.numberKeys) {
      group[key] = Number(document.getElementById(key).value);
    }
    for (const key of cfg.intKeys) {
      group[key] = parseInt(document.getElementById(key).value, 10);
    }
    for (const key of cfg.stringKeys) {
      group[key] = document.getElementById(key).value;
    }
    body[cfg.group] = group;
  }
  return body;
}

// Centre-stone shape (RNG-23, widened to six cuts in RNG-33). `stone_diameter`
// is the WIDTH; the long axis is width * length_ratio. A round stone is always
// ratio 1.0 whatever the ratio box happens to hold, so a stale value can never
// elongate a round stone.
//
// An OVAL at ratio 1.0 is sent as round, because it IS a circle and recording it
// as oval would be a claim the geometry then has to special-case. That rule is
// about oval, not about 1.0: a square cushion is genuinely 1.00 and still has
// rounded corners and bowed sides, so it stays a cushion.
function stoneShapeFields() {
  const shape = document.getElementById("shape").value;
  const ratio = Number(document.getElementById("length_ratio").value);
  if (shape === "round" || !(ratio > 0)) {
    return { shape: "round", length_ratio: 1 };
  }
  if (shape === "oval" && !(ratio > 1)) {
    return { shape: "round", length_ratio: 1 };
  }
  return { shape: shape, length_ratio: ratio };
}

// Each cut carries its own ratio band as data attributes on its <option>, served
// from `ringcad.ringspec.cuts.cut_catalogue()` so the numbers are not retyped
// here (docs/adr/0002). A round stone has no ratio to set, so the box is
// disabled rather than left live with no effect.
function selectedCut() {
  const select = document.getElementById("shape");
  return select.options[select.selectedIndex];
}

function applyShapeState() {
  const cut = selectedCut();
  const ratio = document.getElementById("length_ratio");
  const elongated = cut.dataset.elongated === "true";
  ratio.disabled = !elongated;
  ratio.min = cut.dataset.minRatio;
  ratio.max = cut.dataset.maxRatio;
  if (!elongated) {
    ratio.value = "1";
    return;
  }
  // Only reach for the cut's conventional default when the value in the box is
  // not something this cut can be. Overwriting unconditionally would DISCARD the
  // ratio the photo flow just measured: `photo.js` pre-fills every field and
  // then dispatches `change` here precisely so this state is recomputed, so an
  // unconditional reset would silently replace vision's reading with a textbook
  // number on every upload -- and the form would look like it had worked.
  const current = Number(ratio.value);
  const lo = Number(cut.dataset.minRatio);
  const hi = Number(cut.dataset.maxRatio);
  if (!(current >= lo && current <= hi)) {
    ratio.value = cut.dataset.defaultRatio;
  }
}

function gatherRequestBody() {
  return gatherStructuredBody();
}

// Show/hide one feature's fieldset and match its required-ness. A hidden
// group is never required, so it never blocks native validation.
//
// Removing HIDES rather than clears: the values stay, so re-adding a feature
// gives back whatever you (or the photo) had put there, instead of silently
// discarding edits on a misclick.
function setFeature(name, active) {
  const cfg = FEATURES[name];
  if (!cfg) return;
  const fieldset = document.getElementById(cfg.fieldset);
  if (fieldset) fieldset.hidden = !active;
  for (const key of cfg.numberKeys.concat(cfg.intKeys, cfg.stringKeys)) {
    const el = document.getElementById(key);
    if (!el) continue;
    if (active) {
      el.setAttribute("required", "required");
    } else {
      el.removeAttribute("required");
    }
  }
}

// Removing is the only feature control the form offers, and it exists for
// one reason: vision is not always right. It read pave shoulders on a photo
// that had them, but it can equally read something that isn't there, and
// without this the user would be stuck generating a ring they can see is
// wrong. There is deliberately no matching "add" — features come from the
// photo, not from a parts picker.
function removeFeature(name) {
  setFeature(name, false);
}

// A channel is cut INTO the band, so it needs the stone plus a MIN_WALL wall
// each side (RNG-19 CP3, docs/parameter-ranges.md). The form's 2.2mm default
// cannot hold any legal accent, so checking Side-stone with stock values
// would post a spec the casting gate rejects. Widen the band to fit instead of
// letting the default path 400 — the user can still narrow it and get the
// server's violation, which names the field and the required width.
const CHANNEL_MIN_WALL = 0.8;

function fitBandToChannel() {
  if (!isFeatureActive("side_stone")) return;
  const bandWidth = document.getElementById("band_width");
  const accent = document.getElementById("accent_stone_diameter");
  if (!bandWidth || !accent) return;
  const needed = Number(accent.value) + 2 * CHANNEL_MIN_WALL;
  if (Number(bandWidth.value) < needed) {
    bandWidth.value = needed.toFixed(1);
  }
}

function setLoading(isLoading) {
  generateBtn.disabled = isLoading;
  if (isLoading) {
    statusEl.textContent = "Generating… this can take up to a minute.";
  }
}

function clearFieldErrors() {
  for (const key of NUMBER_KEYS.concat(["prong_count"], FEATURE_FIELD_KEYS)) {
    const el = document.getElementById(key);
    if (!el) continue;
    el.classList.remove("field-error");
    el.removeAttribute("aria-invalid");
  }
}

function clearResult() {
  if (currentObjectUrl) {
    URL.revokeObjectURL(currentObjectUrl);
    currentObjectUrl = null;
  }
  currentBlob = null;

  errorEl.hidden = true;
  errorMessageEl.textContent = "";
  stderrDetails.hidden = true;
  stderrText.textContent = "";

  downloadBtn.hidden = true;
  downloadBtn.removeAttribute("href");

  clearMeshStatus();
  clearFieldErrors();
}

function clearMeshStatus() {
  meshStatusEl.hidden = true;
  meshStatusEl.textContent = "";
  meshStatusEl.classList.remove("mesh-status--valid", "mesh-status--invalid");
}

function renderMeshStatus(valid, repaired, detail) {
  meshStatusEl.classList.remove("mesh-status--valid", "mesh-status--invalid");
  meshStatusEl.classList.add(valid ? "mesh-status--valid" : "mesh-status--invalid");
  let text = valid ? "Castable mesh" : "Not castable";
  if (repaired) text += " (auto-repaired)";
  if (detail) text += " — " + detail;
  meshStatusEl.textContent = text;
  meshStatusEl.hidden = false;
}

function showSuccess(blob) {
  currentBlob = blob;
  currentObjectUrl = URL.createObjectURL(blob);
  downloadBtn.href = currentObjectUrl;
  downloadBtn.hidden = false;
  statusEl.textContent = "Done — download ready.";
  downloadBtn.focus();
  document.dispatchEvent(new CustomEvent("ring:generated", { detail: { blob } }));
}

function flagField(fieldKey) {
  if (!fieldKey) return null;
  // Structured RingSpec errors name dotted paths (e.g. "shank.band_thickness",
  // "halo.halo_gap"); the trailing segment matches the flat input id.
  const elementId = fieldKey.includes(".") ? fieldKey.split(".").pop() : fieldKey;
  const el = document.getElementById(elementId);
  if (!el) return null;
  el.classList.add("field-error");
  el.setAttribute("aria-invalid", "true");
  return el;
}

function renderError(message, fieldKey, stderr) {
  statusEl.textContent = "";
  errorMessageEl.textContent = message;
  errorEl.hidden = false;

  if (stderr) {
    stderrText.textContent = stderr;
    stderrDetails.hidden = false;
  }

  const flagged = flagField(fieldKey);
  if (flagged) {
    flagged.focus();
  } else {
    errorEl.focus();
  }
}

function showError(httpStatus, data) {
  // data may be null/undefined when the response was not JSON.
  if (httpStatus === 503) {
    renderError(
      "The geometry generator is unavailable right now. Please try again later.",
      null,
      null
    );
    return;
  }

  if (data && typeof data === "object") {
    const error = data.error;
    if (error === "OpenSCAD render failed") {
      renderError(
        "The model could not be generated. See the OpenSCAD output for details.",
        null,
        data.openscad_stderr || ""
      );
      return;
    }
    if (error === "Render timed out") {
      renderError(
        "Generating this ring took too long and was stopped. Try smaller or simpler values.",
        null,
        null
      );
      return;
    }
    if (error || data.detail || data.field) {
      const detail = data.detail || error || "Please check your input values.";
      renderError(detail, data.field || null, null);
      return;
    }
  }

  renderError(`Something went wrong (status ${httpStatus}).`, null, null);
}

async function parseJsonSafe(res) {
  try {
    return await res.json();
  } catch (err) {
    console.warn("Response was not valid JSON", err);
    return null;
  }
}

async function generate(event) {
  event.preventDefault();

  if (!form.checkValidity()) {
    form.reportValidity();
    return;
  }

  clearResult();
  setLoading(true);

  try {
    const res = await fetch("/generate-ring", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(gatherRequestBody()),
    });

    if (res.ok) {
      const valid = res.headers.get("X-Mesh-Valid") === "true";
      const repaired = res.headers.get("X-Mesh-Repaired") === "true";
      const detail = res.headers.get("X-Mesh-Repair-Detail") || "";
      renderMeshStatus(valid, repaired, detail);
      const blob = await res.blob();
      showSuccess(blob);
    } else {
      const data = await parseJsonSafe(res);
      showError(res.status, data);
    }
  } catch (err) {
    console.error("Network error contacting /generate-ring", err);
    renderError("Could not reach the server, try again.", null, null);
  } finally {
    setLoading(false);
  }
}

form.addEventListener("submit", generate);

for (const button of document.querySelectorAll(".remove-feature")) {
  button.addEventListener("click", () => removeFeature(button.dataset.feature));
}

// photo.js drives the same machinery rather than reaching into the form
// itself: it says WHICH features the photo showed, and this decides what
// that means for the DOM (same custom-event convention as ring:generated).
document.addEventListener("ring:set-features", (event) => {
  const detected = (event.detail && event.detail.features) || [];
  for (const name of Object.keys(FEATURES)) {
    setFeature(name, detected.includes(name));
  }
  fitBandToChannel();
});

const accentDiaEl = document.getElementById("accent_stone_diameter");
if (accentDiaEl) accentDiaEl.addEventListener("change", fitBandToChannel);

const shapeSelect = document.getElementById("shape");
shapeSelect.addEventListener("change", applyShapeState);
applyShapeState();
