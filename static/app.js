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

const HALO_NUMBER_KEYS = [
  "halo_stone_diameter",
  "halo_stone_count",
  "halo_gap",
  "halo_stone_height",
];

const archetypeSelect = document.getElementById("archetype");
const haloFields = document.getElementById("halo-fields");

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

// Structured RingSpec JSON (RNG-9 CP4): halo is requested as the full
// discriminated-union shape /generate-ring's structured dispatch expects.
function gatherHaloBody() {
  return {
    archetype: "halo",
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
    },
    halo: {
      halo_stone_diameter: Number(document.getElementById("halo_stone_diameter").value),
      halo_stone_count: parseInt(document.getElementById("halo_stone_count").value, 10),
      halo_gap: Number(document.getElementById("halo_gap").value),
      halo_stone_height: Number(document.getElementById("halo_stone_height").value),
    },
  };
}

function gatherRequestBody() {
  return archetypeSelect.value === "halo" ? gatherHaloBody() : gatherSolitaireBody();
}

// Toggles halo field visibility + required-ness with the archetype selector.
function applyArchetypeVisibility() {
  const isHalo = archetypeSelect.value === "halo";
  haloFields.hidden = !isHalo;
  for (const key of HALO_NUMBER_KEYS) {
    const el = document.getElementById(key);
    if (!el) continue;
    if (isHalo) {
      el.setAttribute("required", "required");
    } else {
      el.removeAttribute("required");
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
  for (const key of NUMBER_KEYS.concat(["prong_count"], HALO_NUMBER_KEYS)) {
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
