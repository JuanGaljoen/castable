"use strict";

// Photo upload -> /classify-ring -> pre-fill the form from the returned
// RingSpec, flagging low-confidence and adjusted fields. Everything stays
// editable.
(function () {
  var MAX_EDGE = 1024;
  // Groups whose {field: value} pairs map 1:1 onto input ids of the same name.
  var SHARED_GROUPS = ["shank", "setting", "stones"];
  // Feature groups: the ones a spec carries are what the photo detected.
  var FEATURE_KEYS = ["halo", "trilogy", "side_stone"];
  // RingSpec envelope keys that are NOT a feature group object.
  var META_KEYS = { version: 1, archetype: 1, shank: 1, setting: 1,
                    stones: 1, confidence: 1, motifs: 1 };
  var LOW_CONFIDENCE = 0.5;

  function $(id) {
    return document.getElementById(id);
  }

  function setStatus(msg) {
    var el = $("photo-status");
    if (el) {
      el.textContent = msg;
    }
  }

  function downscale(file) {
    return new Promise(function (resolve, reject) {
      var url = URL.createObjectURL(file);
      var img = new Image();
      img.onload = function () {
        URL.revokeObjectURL(url);
        var w = img.naturalWidth;
        var h = img.naturalHeight;
        var longest = Math.max(w, h);
        var scale = longest > MAX_EDGE ? MAX_EDGE / longest : 1;
        var cw = Math.max(1, Math.round(w * scale));
        var ch = Math.max(1, Math.round(h * scale));
        var canvas = document.createElement("canvas");
        canvas.width = cw;
        canvas.height = ch;
        var ctx = canvas.getContext("2d");
        ctx.drawImage(img, 0, 0, cw, ch);
        canvas.toBlob(
          function (blob) {
            if (blob) {
              resolve(blob);
            } else {
              reject(new Error("toBlob failed"));
            }
          },
          "image/jpeg",
          0.9
        );
      };
      img.onerror = function () {
        URL.revokeObjectURL(url);
        reject(new Error("image load failed"));
      };
      img.src = url;
    });
  }

  function setField(id, value) {
    var el = $(id);
    if (el && (typeof value === "number" || typeof value === "string")) {
      el.value = String(value);
    }
  }

  function clearLowConfidence() {
    var inputs = document.querySelectorAll(".low-confidence");
    for (var i = 0; i < inputs.length; i++) {
      inputs[i].classList.remove("low-confidence");
    }
    var notes = document.querySelectorAll(".field-lowconf");
    for (var j = 0; j < notes.length; j++) {
      var input = $(notes[j].getAttribute("data-for"));
      if (input) {
        var described = (input.getAttribute("aria-describedby") || "")
          .split(/\s+/)
          .filter(function (t) { return t && t !== notes[j].id; })
          .join(" ");
        if (described) {
          input.setAttribute("aria-describedby", described);
        } else {
          input.removeAttribute("aria-describedby");
        }
      }
      notes[j].parentNode.removeChild(notes[j]);
    }
  }

  // Amber border plus an aria-linked note, so screen readers announce it too.
  function flagLowConfidence(id) {
    var input = $(id);
    if (!input || input.classList.contains("low-confidence")) {
      return;
    }
    input.classList.add("low-confidence");
    var note = document.createElement("span");
    note.className = "field-lowconf";
    note.id = id + "-lowconf";
    note.setAttribute("data-for", id);
    note.textContent = "Low confidence — verify this value.";
    var field = input.closest ? input.closest(".field") : input.parentNode;
    (field || input.parentNode).appendChild(note);
    var described = input.getAttribute("aria-describedby");
    input.setAttribute(
      "aria-describedby",
      described ? described + " " + note.id : note.id
    );
  }

  function clearAdjusted() {
    var inputs = document.querySelectorAll(".adjusted-for-castability");
    for (var i = 0; i < inputs.length; i++) {
      inputs[i].classList.remove("adjusted-for-castability");
    }
    var notes = document.querySelectorAll(".field-adjusted");
    for (var j = 0; j < notes.length; j++) {
      var input = $(notes[j].getAttribute("data-for"));
      if (input) {
        var described = (input.getAttribute("aria-describedby") || "")
          .split(/\s+/)
          .filter(function (t) { return t && t !== notes[j].id; })
          .join(" ");
        if (described) {
          input.setAttribute("aria-describedby", described);
        } else {
          input.removeAttribute("aria-describedby");
        }
      }
      notes[j].parentNode.removeChild(notes[j]);
    }
  }

  // A field the server changed to make the ring castable. Styled differently
  // from low confidence: "vision wasn't sure" is not "we changed this".
  function flagAdjusted(id, from, to) {
    var input = $(id);
    if (!input || input.classList.contains("adjusted-for-castability")) {
      return;
    }
    input.classList.add("adjusted-for-castability");
    var note = document.createElement("span");
    note.className = "field-adjusted";
    note.id = id + "-adjusted";
    note.setAttribute("data-for", id);
    var fromText = typeof from === "number" ? from : null;
    var toText = typeof to === "number" ? to : null;
    note.textContent =
      fromText !== null && toText !== null
        ? "Adjusted from " + fromText + " to " + toText + " to make this ring castable."
        : "Adjusted to make this ring castable.";
    var field = input.closest ? input.closest(".field") : input.parentNode;
    (field || input.parentNode).appendChild(note);
    var described = input.getAttribute("aria-describedby");
    input.setAttribute(
      "aria-describedby",
      described ? described + " " + note.id : note.id
    );
  }

  function detectedFeatures(spec) {
    return FEATURE_KEYS.filter(function (name) {
      return !!spec[name];
    });
  }

  // Pre-fill the form from a RingSpec: show its features, fill every field,
  // flag low-confidence and adjusted values.
  function applySpec(spec, adjustments) {
    clearLowConfidence();
    clearAdjusted();

    document.dispatchEvent(
      new CustomEvent("ring:set-features", {
        detail: { features: detectedFeatures(spec) },
      })
    );

    SHARED_GROUPS.forEach(function (groupKey) {
      var group = spec[groupKey];
      if (group) {
        Object.keys(group).forEach(function (k) {
          setField(k, group[k]);
        });
      }
    });

    // Setting .value fires no change event, so trigger it: otherwise a detected
    // oval's ratio box stays locked.
    var shapeSelect = $("shape");
    if (shapeSelect) {
      shapeSelect.dispatchEvent(new Event("change"));
    }

    // Every non-null feature key is a detected feature's group.
    Object.keys(spec).forEach(function (key) {
      if (!META_KEYS[key] && spec[key] && typeof spec[key] === "object") {
        Object.keys(spec[key]).forEach(function (k) {
          setField(k, spec[key][k]);
        });
      }
    });

    var conf = spec.confidence || {};
    Object.keys(conf).forEach(function (field) {
      if (typeof conf[field] === "number" && conf[field] < LOW_CONFIDENCE) {
        flagLowConfidence(field);
      }
    });

    (adjustments || []).forEach(function (adjustment) {
      // "stones.stone_height" -> input id "stone_height".
      var parts = (adjustment.field || "").split(".");
      var id = parts[parts.length - 1];
      flagAdjusted(id, adjustment.old_value, adjustment.new_value);
    });

    // Values were set silently, so tell app.js to re-check the Generate button.
    document.dispatchEvent(new CustomEvent("ring:spec-applied"));
  }

  function showDetections(data) {
    var el = $("photo-detections");
    if (!el) {
      return;
    }
    // Describes the photo only; the form itself shows what was filled in.
    el.textContent = "Detected: " + (data.detected_style || "ring");
    el.hidden = false;
  }

  function handleSuccess(data) {
    if (data && data.ring_detected && data.spec) {
      var adjustments = data.adjustments || [];
      applySpec(data.spec, adjustments);
      var label = $("estimates-label");
      if (label) {
        label.hidden = false;
      }
      showDetections(data);
      // Only what's specific to this run; the caveat has its own label.
      setStatus(
        adjustments.length
          ? adjustments.length +
              (adjustments.length === 1 ? " value was" : " values were") +
              " adjusted so this ring can be cast (marked below)."
          : ""
      );
    } else {
      setStatus(
        (data && data.note) ||
          "No ring detected — enter parameters manually."
      );
    }
  }

  // Choosing a new photo clears messages about the old one. Field markers stay:
  // the values they warn about are still in the form.
  function clearPhotoFeedback() {
    setStatus("");
    var detections = $("photo-detections");
    if (detections) {
      detections.textContent = "";
      detections.hidden = true;
    }
  }

  function errorMessage(status, data) {
    if (status === 503) {
      return "Photo classification isn't configured. Enter parameters manually below.";
    }
    if (data && (data.detail || data.error)) {
      return data.detail || data.error;
    }
    return "Could not analyse the photo, try again.";
  }

  function onEstimate() {
    var fileInput = $("ring-photo");
    var file = fileInput && fileInput.files ? fileInput.files[0] : null;
    if (!file) {
      setStatus("Choose a JPEG or PNG photo first.");
      return;
    }
    var btn = $("estimate-btn");
    if (btn) {
      btn.disabled = true;
    }
    setStatus("Analysing photo…");

    downscale(file)
      .then(function (blob) {
        var form = new FormData();
        form.append("image", blob, "ring.jpg");
        return fetch("/classify-ring", { method: "POST", body: form });
      })
      .then(function (resp) {
        return resp
          .json()
          .catch(function () {
            return {};
          })
          .then(function (data) {
            if (resp.ok) {
              handleSuccess(data);
            } else {
              setStatus(errorMessage(resp.status, data));
            }
          });
      })
      .catch(function () {
        setStatus("Could not reach the server, try again.");
      })
      .then(function () {
        if (btn) {
          btn.disabled = false;
        }
      });
  }

  document.addEventListener("DOMContentLoaded", function () {
    var btn = $("estimate-btn");
    if (btn) {
      btn.addEventListener("click", onEstimate);
    }
    var fileInput = $("ring-photo");
    if (fileInput) {
      fileInput.addEventListener("change", clearPhotoFeedback);
      // CSS can't tell whether a file input holds a file, so mirror it onto a
      // class (also on load, for a file restored by back-navigation).
      var syncHasFile = function () {
        fileInput.classList.toggle("has-file", fileInput.files.length > 0);
      };
      fileInput.addEventListener("change", syncHasFile);
      syncHasFile();
    }
  });
})();
