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

// Non-solitaire archetypes, each a structured RingSpec group. Keyed by the
// `archetype` value; `group` is the spec key, `fieldset` the toggled <fieldset>
// id, `numberKeys`/`intKeys`/`stringKeys` the group's inputs (numbers via
// Number, ints via parseInt, strings read verbatim — e.g. a <select> value).
// A registry, not an if-chain, so a new archetype is one entry (RNG-10 CP3).
const ARCHETYPES = {
  // Solitaire has no group of its own, but it must still be requested as a
  // structured RingSpec: the legacy flat-7 body carries no `stones` group, so a
  // solitaire sent that way silently drops the centre-stone shape and comes back
  // round (RNG-23). `/generate-ring` accepts either form for solitaire; only the
  // structured one can express a shape.
  solitaire: {
    group: null,
    fieldset: null,
    numberKeys: [],
    intKeys: [],
    stringKeys: [],
  },
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

// Every archetype-group field id (for required-toggling and error clearing).
const ARCHETYPE_FIELD_KEYS = Object.values(ARCHETYPES).flatMap(
  (cfg) => cfg.numberKeys.concat(cfg.intKeys, cfg.stringKeys)
);

const archetypeSelect = document.getElementById("archetype");

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

function gatherSolitaireBody() {
  const params = {};
  for (const key of NUMBER_KEYS) {
    params[key] = Number(document.getElementById(key).value);
  }
  params.prong_count = parseInt(document.getElementById("prong_count").value, 10);
  return params;
}

// Structured RingSpec JSON (RNG-9 CP4): a non-solitaire archetype is requested
// as the full discriminated-union shape /generate-ring's structured dispatch
// expects — shared shank/setting/stones plus the archetype's own group.
function gatherStructuredBody(name) {
  const cfg = ARCHETYPES[name];
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
  const body = {
    archetype: name,
    shank: {
      inner_diameter: Number(document.getElementById("inner_diameter").value),
      band_width: Number(document.getElementById("band_width").value),
      band_thickness: Number(document.getElementById("band_thickness").value),
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
  // Solitaire has no group of its own; the schema forbids extra keys, so an
  // empty one cannot be sent.
  if (cfg.group) body[cfg.group] = group;
  return body;
}

// Centre-stone shape (RNG-23). `stone_diameter` is the WIDTH; the long axis is
// width * length_ratio. A round stone is always ratio 1.0 whatever the ratio box
// happens to hold, so a stale value can never elongate a round stone.
function stoneShapeFields() {
  const shape = document.getElementById("shape").value;
  const ratio = Number(document.getElementById("length_ratio").value);
  if (shape !== "oval" || !(ratio > 1)) {
    return { shape: "round", length_ratio: 1 };
  }
  return { shape: "oval", length_ratio: ratio };
}

// The ratio only means anything for an oval, so it is disabled (and reset) for a
// round stone rather than left as a live control with no effect.
function applyShapeState() {
  const isOval = document.getElementById("shape").value === "oval";
  const ratio = document.getElementById("length_ratio");
  ratio.disabled = !isOval;
  if (!isOval) ratio.value = "1";
}

function gatherRequestBody() {
  return ARCHETYPES[archetypeSelect.value]
    ? gatherStructuredBody(archetypeSelect.value)
    : gatherSolitaireBody();
}

// Toggles each archetype's fieldset visibility + required-ness with the
// selector: the active archetype's group is shown and required, all others
// hidden and optional (so a hidden group never blocks native validation).
function applyArchetypeVisibility() {
  const active = archetypeSelect.value;
  for (const [name, cfg] of Object.entries(ARCHETYPES)) {
    const isActive = name === active;
    const fieldset = document.getElementById(cfg.fieldset);
    if (fieldset) fieldset.hidden = !isActive;
    for (const key of cfg.numberKeys.concat(cfg.intKeys, cfg.stringKeys)) {
      const el = document.getElementById(key);
      if (!el) continue;
      if (isActive) {
        el.setAttribute("required", "required");
      } else {
        el.removeAttribute("required");
      }
    }
  }
}

function setLoading(isLoading) {
  generateBtn.disabled = isLoading;
  if (isLoading) {
    statusEl.textContent = "Generating… this can take up to a minute.";
  }
}

function clearFieldErrors() {
  for (const key of NUMBER_KEYS.concat(["prong_count"], ARCHETYPE_FIELD_KEYS)) {
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
archetypeSelect.addEventListener("change", applyArchetypeVisibility);
applyArchetypeVisibility();

const shapeSelect = document.getElementById("shape");
shapeSelect.addEventListener("change", applyShapeState);
applyShapeState();
