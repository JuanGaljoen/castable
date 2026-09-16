"use strict";

// RNG-6 + RNG-12: photo upload -> /classify-ring -> pre-fill the ring form as a
// structured editor over a RingSpec. Plain script (no modules), operates by id.
// The endpoint returns {ring_detected, detected_style, note, spec}; `spec` is a
// full, validated RingSpec (shank/setting/stones + whichever of halo/trilogy/
// side_stone are present + shared-field confidence). RNG-24: any subset of
// features can be present at once, so we check every feature the spec
// actually carries (not a single selected archetype), pre-fill every field,
// and flag low-confidence estimates. Every field stays editable.
(function () {
  var MAX_EDGE = 1024;
  // Groups whose {field: value} pairs map 1:1 onto input ids of the same name.
  var SHARED_GROUPS = ["shank", "setting", "stones"];
  // Feature-group spec keys (RNG-24). Which of these a spec carries is what
  // the photo "detected"; app.js owns what that means for the form.
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

  // Clear any adjusted-for-castability markers left by a previous estimate
  // run (RNG-32), mirroring clearLowConfidence.
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

  // Flag a field RNG-32's coherence repair moved to make the spec buildable:
  // dashed indigo border + an aria-linked note distinct from low-confidence's
  // amber one, so a user can tell "vision wasn't sure" from "we changed
  // this so it can be cast" -- both are true estimates-need-verifying states,
  // but they mean different things.
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

  // Pre-fill the form from a RingSpec: announce every feature the spec
  // actually carries (RNG-24 — any subset, not one archetype) so app.js
  // reveals those fieldsets, fill shared + group fields, then flag any
  // low-confidence shared estimate and any field RNG-32's coherence repair
  // adjusted to make the spec buildable. The user corrects numbers; they are
  // never asked to assemble the ring themselves.
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

    // `setField` assigns `.value` silently, but the shape select drives whether
    // `length_ratio` is editable, and that state is only recomputed on change.
    // Without this a detected oval would arrive with its ratio locked, so the
    // user could see the estimate but not correct it.
    var shapeSelect = $("shape");
    if (shapeSelect) {
      shapeSelect.dispatchEvent(new Event("change"));
    }

    // Every non-meta, non-null key is a PRESENT feature's own group object —
    // any subset can be present at once (RNG-24), not one archetype's worth.
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
      // adjustment.field is a dotted RingSpec path (e.g. "stones.stone_height");
      // the form's input ids are the bare field name, same convention `conf`
      // above already relies on.
      var parts = (adjustment.field || "").split(".");
      var id = parts[parts.length - 1];
      flagAdjusted(id, adjustment.old_value, adjustment.new_value);
    });
  }

  function showDetections(data) {
    var el = $("photo-detections");
    if (!el) {
      return;
    }
    // Describes the PHOTO, nothing else. What the app then did with it is
    // visible in the form itself -- the matching sections appear, already
    // filled in -- so narrating it here only repeated the UI in internal
    // vocabulary.
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
      // Three places were all saying a version of the same thing: the
      // detections line describes the photo, the standing "Estimates only"
      // label carries the caveat, so the status line keeps ONLY what is
      // actionable and specific to this run.
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

  // RNG-29: feedback about the photo must not outlive the photo. Both the
  // status line and the detections line describe whatever file is in the
  // input, so choosing a different one retires both -- otherwise a stale
  // "Choose a JPEG or PNG photo first." reads as though the file just chosen
  // was rejected, and "Detected: ..." keeps asserting the previous photo's
  // style over the new one.
  //
  // Field markers are deliberately NOT cleared here: the estimates they
  // caution about are still sitting in the form. Dropping the caution while
  // its suspect value stays is worse than a stale caution. applySpec clears
  // them on the next successful run, when the values change too.
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
    }
  });
})();
