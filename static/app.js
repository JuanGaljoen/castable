// Ring form controller: form -> RingSpec JSON -> POST /generate-ring -> result.
"use strict";

const NUMBER_KEYS = [
  "inner_diameter",
  "band_width",
  "band_thickness",
  "stone_diameter",
  "stone_height",
  "setting_height",
];

// Optional ring features, any mix. A registry, so a new feature is one entry.
// Features come only from the photo; the form can remove one but never add one.
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

const FEATURE_FIELD_KEYS = Object.values(FEATURES).flatMap(
  (cfg) => cfg.numberKeys.concat(cfg.intKeys, cfg.stringKeys)
);

// Visibility is the state, so there's no separate flag to drift.
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
const announceEl = document.getElementById("generate-announce");
const generateHintEl = document.getElementById("generate-hint");

// Last successful request. Generate is disabled while the form would send the
// same thing again (a rebuild takes up to a minute and shows nothing new).
let lastGeneratedBody = null;
let generating = false;
const errorEl = document.getElementById("error");
const errorMessageEl = document.getElementById("error-message");
const downloadBtn = document.getElementById("download-btn");
const downloadMenuEl = document.querySelector(".download-menu");
const downloadOptionsEl = document.getElementById("download-options");
const meshStatusEl = document.getElementById("mesh-status");

// The last generated STL, for Download.
let currentBlob = null;
let currentObjectUrl = null;
// The in-flight STEP build, so a new Generate can cancel it.
let stepController = null;

// Form -> RingSpec JSON: shank, setting, stones, plus one group per active
// feature.
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

// Stone shape. Round always sends ratio 1.0; an oval at 1.0 is a circle, so it
// is sent as round.
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

// Each cut's ratio band comes from the server on its <option> (docs/adr/0002).
// Round has no ratio, so the box is disabled.
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

// Show or hide a feature. Hidden fields aren't required, and their values are
// kept rather than cleared.
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

// Remove exists because vision can be wrong. There is deliberately no "add".
function removeFeature(name) {
  setFeature(name, false);
}

// A channel needs the stone plus a wall each side, and the default 2.2mm band
// is too narrow, so widen it to fit. The server still rejects anything smaller.
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

function syncGenerateEnabled() {
  if (generating) return;
  const unchanged =
    lastGeneratedBody !== null &&
    JSON.stringify(gatherRequestBody()) === lastGeneratedBody;
  generateBtn.disabled = unchanged;
  generateHintEl.hidden = !unchanged;
}

function setLoading(isLoading) {
  generating = isLoading;
  generateBtn.disabled = isLoading;
  if (isLoading) generateHintEl.hidden = true;
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

  if (stepController) stepController.abort();
  closeDownloadMenu(false);
  downloadMenuEl.hidden = true;
  announceEl.textContent = "";

  clearMeshStatus();
  clearFieldErrors();
}

function clearMeshStatus() {
  meshStatusEl.hidden = true;
  meshStatusEl.textContent = "";
  meshStatusEl.classList.remove("mesh-status--valid", "mesh-status--invalid");
}

function renderMeshStatus(valid, repaired, detail) {
  // A clean mesh is the norm, so only show a status when something is off.
  if (valid && !repaired) {
    clearMeshStatus();
    return;
  }
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
  downloadMenuEl.hidden = false;
  // The render + Download appearing is the visible success; this is for AT.
  statusEl.textContent = "";
  announceEl.textContent = "Done — download ready.";
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

function renderError(message, fieldKey) {
  statusEl.textContent = "";
  errorMessageEl.textContent = message;
  errorEl.hidden = false;

  const flagged = flagField(fieldKey);
  if (flagged) {
    flagged.focus();
  } else {
    errorEl.focus();
  }
}

function showError(httpStatus, data) {
  // data may be null/undefined when the response was not JSON.
  if (data && typeof data === "object" && (data.error || data.detail || data.field)) {
    const detail = data.detail || data.error || "Please check your input values.";
    renderError(detail, data.field || null);
    return;
  }
  renderError(`Something went wrong (status ${httpStatus}).`, null);
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

  const requestBody = JSON.stringify(gatherRequestBody());
  if (requestBody === lastGeneratedBody) return;   // Enter in a field

  clearResult();
  setLoading(true);

  try {
    const res = await fetch("/generate-ring", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: requestBody,
    });

    if (res.ok) {
      const valid = res.headers.get("X-Mesh-Valid") === "true";
      const repaired = res.headers.get("X-Mesh-Repaired") === "true";
      const detail = res.headers.get("X-Mesh-Repair-Detail") || "";
      renderMeshStatus(valid, repaired, detail);
      const blob = await res.blob();
      lastGeneratedBody = requestBody;
      showSuccess(blob);
    } else {
      const data = await parseJsonSafe(res);
      showError(res.status, data);
    }
  } catch (err) {
    console.error("Network error contacting /generate-ring", err);
    renderError("Could not reach the server, try again.", null);
  } finally {
    setLoading(false);
    syncGenerateEnabled();
  }
}

// ---- Download format menu --------------------------------------------------
// WAI-ARIA menu button: Enter/Space/ArrowDown open on the first item,
// ArrowUp on the last; arrows/Home/End move; Escape closes back to the
// trigger; Tab or a click elsewhere just closes.
function menuItems() {
  return Array.from(downloadOptionsEl.querySelectorAll('[role="menuitem"]'));
}

function openDownloadMenu(focusLast) {
  downloadOptionsEl.hidden = false;
  downloadBtn.setAttribute("aria-expanded", "true");
  const items = menuItems();
  items[focusLast ? items.length - 1 : 0].focus();
}

function closeDownloadMenu(returnFocus) {
  if (downloadOptionsEl.hidden) return;
  downloadOptionsEl.hidden = true;
  downloadBtn.setAttribute("aria-expanded", "false");
  if (returnFocus) downloadBtn.focus();
}

function saveBlobUrl(url, filename) {
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  a.remove();
}

// The STL is already in memory: it is what the viewer rendered.
function downloadStl() {
  if (currentObjectUrl) saveBlobUrl(currentObjectUrl, "ring.stl");
}

function setStepBusy(busy) {
  downloadBtn.classList.toggle("is-busy", busy);
  if (busy) downloadBtn.setAttribute("aria-busy", "true");
  else downloadBtn.removeAttribute("aria-busy");
}

// STEP is rebuilt from the request that drew the preview, not the live form,
// which may have changed since.
async function downloadStep() {
  if (stepController || lastGeneratedBody === null) return;
  stepController = new AbortController();
  setStepBusy(true);
  announceEl.textContent = "Preparing STEP file… this can take up to a minute.";
  try {
    const res = await fetch("/generate-ring?format=step", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: lastGeneratedBody,
      signal: stepController.signal,
    });
    if (!res.ok) {
      announceEl.textContent = "";
      showError(res.status, await parseJsonSafe(res));
      return;
    }
    const url = URL.createObjectURL(await res.blob());
    saveBlobUrl(url, "ring.step");
    URL.revokeObjectURL(url);
    announceEl.textContent = "STEP download ready.";
  } catch (err) {
    if (err.name === "AbortError") return;   // a new Generate replaced the ring
    console.error("Network error building STEP", err);
    announceEl.textContent = "";
    renderError("Could not build the STEP file, try again.", null);
  } finally {
    stepController = null;
    setStepBusy(false);
  }
}

downloadBtn.addEventListener("click", () => {
  if (stepController) return;
  if (downloadOptionsEl.hidden) openDownloadMenu(false);
  else closeDownloadMenu(true);
});

downloadBtn.addEventListener("keydown", (event) => {
  if (stepController) return;
  if (event.key === "ArrowDown" || event.key === "ArrowUp") {
    event.preventDefault();
    openDownloadMenu(event.key === "ArrowUp");
  }
});

downloadOptionsEl.addEventListener("keydown", (event) => {
  const items = menuItems();
  const i = items.indexOf(document.activeElement);
  const moves = {
    ArrowDown: (i + 1) % items.length,
    ArrowUp: (i - 1 + items.length) % items.length,
    Home: 0,
    End: items.length - 1,
  };
  if (event.key in moves) {
    event.preventDefault();
    items[moves[event.key]].focus();
  } else if (event.key === "Escape") {
    event.preventDefault();
    closeDownloadMenu(true);
  } else if (event.key === "Tab") {
    closeDownloadMenu(false);
  }
});

downloadOptionsEl.addEventListener("click", (event) => {
  const item = event.target.closest('[role="menuitem"]');
  if (!item) return;
  closeDownloadMenu(true);
  if (item.dataset.format === "step") downloadStep();
  else downloadStl();
});

document.addEventListener("click", (event) => {
  if (!downloadMenuEl.contains(event.target)) closeDownloadMenu(false);
});

form.addEventListener("submit", generate);
form.addEventListener("input", syncGenerateEnabled);
form.addEventListener("change", syncGenerateEnabled);
document.addEventListener("ring:spec-applied", syncGenerateEnabled);

for (const button of document.querySelectorAll(".remove-feature")) {
  button.addEventListener("click", () => {
    removeFeature(button.dataset.feature);
    syncGenerateEnabled();
  });
}

// photo.js says which features the photo showed; this applies them.
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

// Editing a flagged field clears its red marker. The error message stays,
// since it holds the instruction being followed.
for (const key of NUMBER_KEYS.concat(["prong_count"], FEATURE_FIELD_KEYS)) {
  const el = document.getElementById(key);
  if (!el) continue;
  el.addEventListener("input", () => {
    el.classList.remove("field-error");
    el.removeAttribute("aria-invalid");
  });
}
