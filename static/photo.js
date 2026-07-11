"use strict";

// RNG-6 + RNG-12: photo upload -> /classify-ring -> pre-fill the ring form as a
// structured editor over a RingSpec. Plain script (no modules), operates by id.
// The endpoint returns {ring_detected, detected_style, note, spec}; `spec` is a
// full, validated RingSpec (archetype + shank/setting/stones + the archetype's
// group + shared-field confidence). We select the detected archetype, pre-fill
// every field, and flag low-confidence estimates. Every field stays editable.
(function () {
  var MAX_EDGE = 1024;
  // Groups whose {field: value} pairs map 1:1 onto input ids of the same name.
  var SHARED_GROUPS = ["shank", "setting", "stones"];
  // RingSpec envelope keys that are NOT an archetype group object.
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

  // Clear any low-confidence markers left by a previous estimate run, so a
  // re-run never leaves a stale caution on a field it's now confident about.
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

  // Flag a field as a low-confidence estimate: amber border + an aria-linked
  // caution note, so screen readers announce it too. WCAG 2.1 AA.
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

  // Pre-fill the form from a RingSpec: select the detected archetype (and fire
  // change so app.js toggles the right fieldset), fill shared + group fields,
  // then flag any low-confidence shared estimate.
  function applySpec(spec) {
    clearLowConfidence();

    var select = $("archetype");
    if (select && spec.archetype) {
      select.value = spec.archetype;
      select.dispatchEvent(new Event("change"));
    }

    SHARED_GROUPS.forEach(function (groupKey) {
      var group = spec[groupKey];
      if (group) {
        Object.keys(group).forEach(function (k) {
          setField(k, group[k]);
        });
      }
    });

    // The one non-meta key is the active archetype's own group object.
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
  }

  function showDetections(data, spec) {
    var el = $("photo-detections");
    if (!el) {
      return;
    }
    var text = "Detected: " + (data.detected_style || "ring");
    if (spec && spec.archetype) {
      text += " · building " + spec.archetype.replace(/_/g, " ");
    }
    el.textContent = text;
    el.hidden = false;
  }

  function handleSuccess(data) {
    if (data && data.ring_detected && data.spec) {
      applySpec(data.spec);
      var label = $("estimates-label");
      if (label) {
        label.hidden = false;
      }
      showDetections(data, data.spec);
      setStatus(data.note || "Estimates applied. Verify before generating.");
    } else {
      setStatus(
        (data && data.note) ||
          "No ring detected — enter parameters manually."
      );
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
  });
})();
