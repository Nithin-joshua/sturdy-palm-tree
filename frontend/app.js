(() => {
  "use strict";

  // State Management
  const state = {
    step: 1,
    imageFile: null,
    imagePreviewUrl: null,
    standardType: "builtin",
    standardFile: null,
    sensorFile: null,
    visionHints: null,
    currentReport: null,
    annotatedUrl: null,
  };

  const $ = (id) => document.getElementById(id);

  function getApiBase() {
    if (window.APP_CONFIG && typeof window.APP_CONFIG.apiBase === "string") {
      return window.APP_CONFIG.apiBase;
    }
    return "";
  }

  function escapeHtml(str) {
    if (!str && str !== 0) return "";
    return String(str)
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;")
      .replace(/'/g, "&#039;");
  }

  function formatBytes(bytes) {
    if (!bytes || bytes === 0) return "0 B";
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
    return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
  }

  // ==========================================================================
  // Toast Notifications
  // ==========================================================================
  function showToast(message, isError = false) {
    const container = $("toastContainer");
    if (!container) return;

    const toast = document.createElement("div");
    toast.className = `toast ${isError ? "toast-error" : ""}`;
    toast.innerHTML = `
      <span>${isError ? "⚠" : "ℹ"}</span>
      <span>${escapeHtml(message)}</span>
    `;
    container.appendChild(toast);

    setTimeout(() => {
      toast.style.opacity = "0";
      toast.style.transition = "opacity 0.2s ease";
      setTimeout(() => toast.remove(), 200);
    }, 3500);
  }

  // ==========================================================================
  // Stepper & Step Transitions (Shared-axis slide + fade)
  // ==========================================================================
  function goToStep(stepNum) {
    state.step = stepNum;

    // Slim Stepper Text Highlights
    [1, 2, 3].forEach((n) => {
      const lbl = $(`step${n}Label`);
      if (!lbl) return;
      lbl.classList.remove("is-active", "is-done");
      if (n === stepNum) {
        lbl.classList.add("is-active");
      } else if (n < stepNum) {
        lbl.classList.add("is-done");
      }
    });

    // Panel Toggling
    [1, 2, 3].forEach((n) => {
      const panel = $(`stepPanel${n}`);
      if (panel) {
        panel.hidden = n !== stepNum;
      }
    });
  }

  // ==========================================================================
  // Left Hero Canvas Management
  // ==========================================================================
  function updateHeroCanvas() {
    const empty = $("canvasEmpty");
    const frame = $("imageFrame");
    const img = $("heroImage");
    const meta = $("canvasMeta");
    const scanLine = $("scanLine");
    const bboxSvg = $("bboxSvg");
    const bboxChip = $("bboxChip");
    const toolbar = $("stageToolbar");

    if (state.imagePreviewUrl) {
      if (empty) empty.hidden = true;
      if (frame) frame.hidden = false;
      if (meta) meta.hidden = false;
      if (toolbar) toolbar.hidden = false;
      if (img) {
        img.src = state.imagePreviewUrl;
        img.onload = () => {
          if (img.naturalWidth && img.naturalHeight) {
            const metaDim = $("metaDim");
            if (metaDim) metaDim.textContent = `${img.naturalWidth}×${img.naturalHeight}`;
          }
        };
      }

      // Scan line sweeps once on photo upload
      if (scanLine) {
        scanLine.className = "scan-line sweeping-once";
        setTimeout(() => {
          scanLine.className = "scan-line";
        }, 900);
      }

      $("metaFile").textContent = state.imageFile ? state.imageFile.name : "sample.png";
      $("metaSize").textContent = state.imageFile ? formatBytes(state.imageFile.size) : "512 KB";
      if (!img.naturalWidth) {
        $("metaDim").textContent = "—";
      }
      $("metaStatus").textContent = "READY";

      if (bboxSvg) bboxSvg.setAttribute("hidden", "");
      if (bboxChip) bboxChip.hidden = true;
    } else {
      if (frame) frame.hidden = true;
      if (empty) empty.hidden = false;
      if (meta) meta.hidden = true;
      if (toolbar) toolbar.hidden = true;
      if (img) img.src = "";
      if (bboxSvg) bboxSvg.setAttribute("hidden", "");
      if (bboxChip) bboxChip.hidden = true;
    }
  }

  // ==========================================================================
  // Step 1: Photo & Samples
  // ==========================================================================
  function initStep1() {
    const dropzone = $("imageDropzone");
    const input = $("imageInput");
    const idle = $("dropzoneIdle");
    const selected = $("dropzoneSelected");
    const thumb = $("selectedThumb");
    const nameEl = $("selectedName");
    const sizeEl = $("selectedSize");
    const removeBtn = $("btnRemoveImage");
    const nextBtn = $("btnNext1");

    function validateImage(file) {
      if (!file.type.startsWith("image/")) {
        return "Please upload an image file (PNG, JPG, WEBP).";
      }
      if (file.size > 5 * 1024 * 1024) {
        return `File exceeds 5 MB limit (${formatBytes(file.size)}).`;
      }
      return null;
    }

    function setImage(file) {
      const err = validateImage(file);
      if (err) {
        showToast(err, true);
        return false;
      }

      state.imageFile = file;
      if (state.imagePreviewUrl) {
        URL.revokeObjectURL(state.imagePreviewUrl);
      }
      state.imagePreviewUrl = URL.createObjectURL(file);

      thumb.src = state.imagePreviewUrl;
      nameEl.textContent = file.name;
      sizeEl.textContent = formatBytes(file.size);

      idle.hidden = true;
      selected.hidden = false;
      nextBtn.disabled = false;

      updateHeroCanvas();
      return true;
    }

    function clearImage() {
      state.imageFile = null;
      if (state.imagePreviewUrl) {
        URL.revokeObjectURL(state.imagePreviewUrl);
        state.imagePreviewUrl = null;
      }
      input.value = "";
      idle.hidden = false;
      selected.hidden = true;
      nextBtn.disabled = true;

      updateHeroCanvas();
    }

    dropzone.addEventListener("click", (e) => {
      if (e.target.closest("#btnRemoveImage")) return;
      input.click();
    });

    dropzone.addEventListener("keydown", (e) => {
      if (e.key === "Enter" || e.key === " ") {
        e.preventDefault();
        input.click();
      }
    });

    input.addEventListener("change", () => {
      if (input.files && input.files[0]) {
        setImage(input.files[0]);
      }
    });

    ["dragenter", "dragover"].forEach((eventName) => {
      dropzone.addEventListener(eventName, (e) => {
        e.preventDefault();
        e.stopPropagation();
        dropzone.classList.add("is-dragover");
      });
    });

    ["dragleave", "drop"].forEach((eventName) => {
      dropzone.addEventListener(eventName, (e) => {
        e.preventDefault();
        e.stopPropagation();
        dropzone.classList.remove("is-dragover");
      });
    });

    dropzone.addEventListener("drop", (e) => {
      const dt = e.dataTransfer;
      if (dt && dt.files && dt.files[0]) {
        setImage(dt.files[0]);
      }
    });

    removeBtn.addEventListener("click", (e) => {
      e.stopPropagation();
      clearImage();
    });

    nextBtn.addEventListener("click", () => {
      if (state.imageFile) {
        goToStep(2);
      }
    });

    // Sample buttons
    $("sampleCrack").addEventListener("click", () => loadSample("crack"));
    $("sampleCorrosion").addEventListener("click", () => loadSample("corrosion"));
    if ($("sampleScratch")) {
      $("sampleScratch").addEventListener("click", () => loadSample("scratch"));
    }
  }

  // ==========================================================================
  // Sample Data Loading
  // ==========================================================================
  async function loadSample(sampleType) {
    try {
      showToast(`Loading ${sampleType} sample bundle...`);

      let imgPath = "samples/sample_defect.png";
      let imgFilename = "sample_defect.png";
      if (sampleType === "corrosion") {
        imgPath = "samples/sample_corrosion.png";
        imgFilename = "sample_corrosion.png";
      } else if (sampleType === "scratch") {
        imgPath = "samples/sample_scratch.png";
        imgFilename = "sample_scratch.png";
      }

      const imgRes = await fetch(imgPath);
      if (!imgRes.ok) throw new Error("Could not load sample image.");
      const imgBlob = await imgRes.blob();
      const imgFile = new File([imgBlob], imgFilename, { type: "image/png" });

      state.imageFile = imgFile;
      if (state.imagePreviewUrl) URL.revokeObjectURL(state.imagePreviewUrl);
      state.imagePreviewUrl = URL.createObjectURL(imgFile);

      $("selectedThumb").src = state.imagePreviewUrl;
      $("selectedName").textContent = imgFile.name;
      $("selectedSize").textContent = formatBytes(imgFile.size);
      $("dropzoneIdle").hidden = true;
      $("dropzoneSelected").hidden = false;
      $("btnNext1").disabled = false;

      // Standard
      const stdRes = await fetch("samples/sample_standard.md");
      if (stdRes.ok) {
        const stdBlob = await stdRes.blob();
        state.standardFile = new File([stdBlob], "sample_standard.md", { type: "text/markdown" });
      }
      state.standardType = "builtin";
      $("standardSelect").value = "builtin";
      $("customDocBox").hidden = true;

      // Sensor telemetry CSV
      const csvRes = await fetch("samples/sample_sensors.csv");
      if (csvRes.ok) {
        const csvBlob = await csvRes.blob();
        state.sensorFile = new File([csvBlob], "sample_sensors.csv", { type: "text/csv" });
        $("sensorName").textContent = "sample_sensors.csv";
        $("sensorChip").hidden = false;
      }

      if (sampleType === "crack") {
        $("objectNameInput").value = "pipeline_segment_A12";
        state.visionHints = {
          defect_type: "crack",
          confidence: 0.92,
          bounding_box: { x: 0.22, y: 0.18, width: 0.38, height: 0.60 }
        };
      } else if (sampleType === "corrosion") {
        $("objectNameInput").value = "storage_tank_floor_B04";
        state.visionHints = {
          defect_type: "corrosion",
          confidence: 0.88,
          bounding_box: { x: 0.15, y: 0.25, width: 0.65, height: 0.45 }
        };
      } else if (sampleType === "scratch") {
        $("objectNameInput").value = "turbine_blade_C09";
        state.visionHints = {
          defect_type: "scratch",
          confidence: 0.85,
          bounding_box: { x: 0.28, y: 0.35, width: 0.42, height: 0.22 }
        };
      }

      updateHeroCanvas();
      goToStep(3);
      showToast("Sample loaded successfully. Ready to run.", false);
    } catch (err) {
      showToast(`Sample load error: ${err.message}`, true);
    }
  }

  // ==========================================================================
  // Step 2: Inspection Standard
  // ==========================================================================
  function initStep2() {
    const select = $("standardSelect");
    const customBox = $("customDocBox");
    const input = $("standardInput");
    const pickBtn = $("btnPickDoc");
    const chip = $("standardChip");
    const nameEl = $("standardName");
    const removeBtn = $("btnRemoveStandard");
    const backBtn = $("btnBack2");
    const nextBtn = $("btnNext2");

    select.addEventListener("change", () => {
      state.standardType = select.value;
      if (select.value === "custom") {
        customBox.hidden = false;
        nextBtn.disabled = !state.standardFile;
      } else {
        customBox.hidden = true;
        nextBtn.disabled = false;
      }
    });

    pickBtn.addEventListener("click", () => input.click());

    input.addEventListener("change", () => {
      if (input.files && input.files[0]) {
        const file = input.files[0];
        state.standardFile = file;
        nameEl.textContent = file.name;
        chip.hidden = false;
        nextBtn.disabled = false;
      }
    });

    removeBtn.addEventListener("click", () => {
      state.standardFile = null;
      input.value = "";
      chip.hidden = true;
      if (state.standardType === "custom") {
        nextBtn.disabled = true;
      }
    });

    backBtn.addEventListener("click", () => goToStep(1));
    nextBtn.addEventListener("click", () => goToStep(3));
  }

  // ==========================================================================
  // Step 3: Run & Execution
  // ==========================================================================
  function initStep3() {
    const pickBtn = $("btnPickSensor");
    const input = $("sensorInput");
    const chip = $("sensorChip");
    const nameEl = $("sensorName");
    const removeBtn = $("btnRemoveSensor");
    const backBtn = $("btnBack3");
    const runBtn = $("btnRun");

    pickBtn.addEventListener("click", () => input.click());

    input.addEventListener("change", () => {
      if (input.files && input.files[0]) {
        const file = input.files[0];
        state.sensorFile = file;
        nameEl.textContent = file.name;
        chip.hidden = false;
      }
    });

    removeBtn.addEventListener("click", () => {
      state.sensorFile = null;
      input.value = "";
      chip.hidden = true;
    });

    backBtn.addEventListener("click", () => goToStep(2));

    async function ensureStandardFile() {
      if (state.standardType === "builtin" && !state.standardFile) {
        const res = await fetch("samples/sample_standard.md");
        if (res.ok) {
          const blob = await res.blob();
          state.standardFile = new File([blob], "sample_standard.md", { type: "text/markdown" });
        }
      }
    }

    async function executeInspection() {
      if (!state.imageFile) {
        showToast("Please upload an inspection defect photo first.", true);
        goToStep(1);
        return;
      }

      await ensureStandardFile();

      if (!state.standardFile) {
        showToast("Standard document could not be loaded.", true);
        return;
      }

      const form = $("flowForm");
      const loader = $("pipelineLoader");
      const resultView = $("flowResult");
      const scanLine = $("scanLine");

      // Switch to loader view
      form.hidden = true;
      loader.hidden = false;
      resultView.hidden = true;

      // Scan line loops during inspection execution
      if (scanLine) {
        scanLine.className = "scan-line looping";
      }

      // Simulate 3-stage pipeline animation
      $("stageInd1").innerHTML = '<span class="stage-spin"></span>';
      $("stage1").className = "pipeline-stage is-active";
      $("stageInd2").textContent = "○";
      $("stage2").className = "pipeline-stage";
      $("stageInd3").textContent = "○";
      $("stage3").className = "pipeline-stage";

      const t1 = setTimeout(() => {
        $("stageInd1").textContent = "✓";
        $("stage1").className = "pipeline-stage is-done";
        $("stageInd2").innerHTML = '<span class="stage-spin"></span>';
        $("stage2").className = "pipeline-stage is-active";
      }, 300);

      const t2 = setTimeout(() => {
        $("stageInd2").textContent = "✓";
        $("stage2").className = "pipeline-stage is-done";
        $("stageInd3").innerHTML = '<span class="stage-spin"></span>';
        $("stage3").className = "pipeline-stage is-active";
      }, 600);

      try {
        const fd = new FormData();
        fd.append("image", state.imageFile);
        fd.append("standard", state.standardFile);
        if (state.sensorFile) {
          fd.append("sensor_csv", state.sensorFile);
        }
        const objName = $("objectNameInput").value.trim();
        if (objName) {
          fd.append("object_name", objName);
        }
        fd.append("annotate", "true");

        if (state.visionHints) {
          fd.append("vision_hints", JSON.stringify(state.visionHints));
        }

        const base = getApiBase();
        const controller = new AbortController();
        const timeoutId = setTimeout(() => controller.abort(), 45000);

        let data;
        let isDemoMode = false;
        try {
          const res = await fetch(`${base}/api/inspect`, {
            method: "POST",
            body: fd,
            signal: controller.signal,
          });
          clearTimeout(timeoutId);
          data = await res.json().catch(() => null);

          if (!res.ok) {
            let msg = `Inspection error (HTTP ${res.status})`;
            if (data && data.detail) {
              msg = typeof data.detail === "string" ? data.detail : JSON.stringify(data.detail);
            }
            throw new Error(msg);
          }
        } catch (fetchErr) {
          clearTimeout(timeoutId);
          console.warn("Backend unavailable, executing simulation mode:", fetchErr);
          isDemoMode = true;
          await new Promise((resolve) => setTimeout(resolve, 600));
          data = generateDemoReport();
        }

        data.is_simulated_demo = isDemoMode;
        state.currentReport = data;
        clearTimeout(t1);
        clearTimeout(t2);

        $("stageInd1").textContent = "✓";
        $("stage1").className = "pipeline-stage is-done";
        $("stageInd2").textContent = "✓";
        $("stage2").className = "pipeline-stage is-done";
        $("stageInd3").textContent = "✓";
        $("stage3").className = "pipeline-stage is-done";

        // Stop looping scan line
        if (scanLine) scanLine.className = "scan-line";
        loader.hidden = true;

        renderHierarchyResult(data);
        resultView.hidden = false;
        $("metaStatus").textContent = isDemoMode ? "DEMO RESULT" : "DIAGNOSED";
        if (isDemoMode) {
          showToast("Backend offline: Loaded demonstration diagnosis report.", false);
        }
      } catch (err) {
        clearTimeout(t1);
        clearTimeout(t2);
        if (scanLine) scanLine.className = "scan-line";
        loader.hidden = true;
        form.hidden = false;
        showToast(err.message || "Failed to complete inspection.", true);
        $("metaStatus").textContent = "ERROR";
      }
    }

    runBtn.addEventListener("click", executeInspection);
  }

  // ==========================================================================
  // Demonstration Fallback Report Generator (Used when backend is offline)
  // ==========================================================================
  function generateDemoReport() {
    const hint = state.visionHints || { defect_type: "crack", confidence: 0.91, bounding_box: { x: 0.32, y: 0.22, width: 0.35, height: 0.55 } };
    const defectType = (hint.defect_type || "crack").toLowerCase();
    const objName = $("objectNameInput").value.trim() || (defectType === "crack" ? "pipeline_segment_A12" : defectType === "corrosion" ? "storage_tank_floor_B04" : "turbine_blade_C09");
    const isCritical = defectType === "crack" || (state.sensorFile != null);

    return {
      inspection_id: `insp_sim_${Math.random().toString(36).substring(2, 10)}`,
      object_name: objName,
      inspection_time: new Date().toISOString(),
      input_data_summary: `image '${state.imageFile ? state.imageFile.name : "sample.png"}', standard '${state.standardFile ? state.standardFile.name : "ISO 5817"}', ${state.sensorFile ? "telemetry log attached" : "no sensor log"}`,
      defect_type: defectType,
      defect_location: defectType === "crack" ? "longitudinal weld seam" : defectType === "corrosion" ? "lower shell plate" : "leading edge chord",
      confidence: hint.confidence || 0.91,
      severity_level: isCritical ? "critical" : defectType === "corrosion" ? "medium" : "low",
      recommended_action: isCritical ? "stop_machine" : defectType === "corrosion" ? "schedule_maintenance" : "reinspect_next_shift",
      risk_explanation: defectType === "crack"
        ? "Linear defect exceeding 5.0 mm located in load-bearing boundary (clause 3.2: serious crack). Telemetry indicates thermal levels above threshold."
        : defectType === "corrosion"
        ? "Localized pitting and oxidation covering approximately 12% of inspected plate surface. Exceeds clause 3.4 standard operational limits."
        : "Superficial linear scratch without structural penetration or wall loss. Conforms to minor discontinuity criteria under clause 3.1.",
      defect_bbox: hint.bounding_box || { x: 0.30, y: 0.20, width: 0.40, height: 0.50 },
      standard_evidence: [
        {
          clause_id: defectType === "crack" ? "3.2" : defectType === "corrosion" ? "3.4" : "3.1",
          title: defectType === "crack" ? "Serious Crack Specification" : defectType === "corrosion" ? "Corrosion Severity Limits" : "Minor Surface Discontinuity",
          text: defectType === "crack"
            ? "A crack longer than 5 mm located in a load-bearing or pressure boundary area shall be classified as a serious defect. Recommended action: repair or reject pending engineering review."
            : defectType === "corrosion"
            ? "Corrosion covering more than 10 percent of the inspected local area or showing pitting shall be classified at least as medium severity. If near a weld, classify as high severity."
            : "A defect is minor when it is superficial, shorter than 5 mm, not located in a load-bearing or pressure boundary area, and no abnormal sensor reading is present.",
          score: 7.31
        },
        {
          clause_id: "2.1",
          title: "Surface Discontinuity Identification",
          text: "Surface discontinuities must be dimensioned, located relative to datum weld lines, and referenced to operational stress planes.",
          score: 6.36
        },
        {
          clause_id: "4.1",
          title: "Engineering Review Escalation",
          text: "Human inspection supervisor review is mandatory whenever severity exceeds acceptable thresholds or sensors indicate threshold deviation.",
          score: 5.92
        }
      ],
      sensor_readings: state.sensorFile ? [
        { name: "temperature", value: 85.0, unit: "°C" },
        { name: "vibration", value: 4.5, unit: "mm/s" },
        { name: "pressure_deviation", value: 7.1, unit: "%" },
        { name: "current", value: 11.8, unit: "A" }
      ] : [],
      requires_human_review: isCritical,
      human_review_reasons: isCritical ? ["Severity level is critical: crack in pressure boundary."] : [],
      audit_hash: "a4f892bc937104e578a1bc4028fae90142b78912ef0984a1d87e02514c3e8912",
      compliance_standard: "ISO 9001:2015 Clause 8.7",
      capa_plan: {
        immediate_containment: isCritical ? "Immediately quarantine component and halt line operation." : "Component released for standard processing.",
        root_cause_analysis: defectType === "crack" ? "High-cycle fatigue crack initiated at welding heat-affected zone." : "Superficial atmospheric oxidation.",
        corrective_action: isCritical ? "Execute structural weld repair procedure WPS-04." : "No corrective intervention required.",
        preventive_action: "Recalibrate seam tracking sensors and verify preheat temperature compliance."
      },
      is_simulated_demo: true
    };
  }

  // ==========================================================================
  // Result Hierarchy Rendering
  // ==========================================================================
  function renderHierarchyResult(r) {
    const sev = (r.severity_level || "low").toLowerCase();
    const actionClean = (r.recommended_action || "reinspect").replace(/_/g, " ");

    const isFail = sev === "critical" || sev === "high" || r.recommended_action === "stop_machine" || r.recommended_action === "reject";
    const verdictText = isFail ? "FAIL" : "PASS";

    // Demo Mode notice
    const demoBanner = $("demoBanner");
    if (demoBanner) {
      demoBanner.hidden = !r.is_simulated_demo;
    }

    // 1. Verdict & Severity Badge
    const verdictSec = $("verdictSection");
    verdictSec.className = `verdict-section ${isFail ? "" : "is-pass"}`;
    $("verdictText").textContent = verdictText;

    const sevBadge = $("severityBadge");
    if (sevBadge) {
      const sevClean = (r.severity_level || "low").toLowerCase();
      sevBadge.textContent = sevClean.charAt(0).toUpperCase() + sevClean.slice(1);
      sevBadge.className = `severity-badge severity-${sevClean}`;
    }

    $("verdictAction").textContent = `Action: ${actionClean.charAt(0).toUpperCase() + actionClean.slice(1)}`;

    // 2. Confidence Fill & Count-up Animation
    const confVal = (r.confidence * 100);
    $("confFill").style.width = "0%";
    setTimeout(() => {
      $("confFill").style.width = `${confVal.toFixed(1)}%`;
    }, 50);

    // Count up percentage
    let start = 0;
    const dur = 400;
    const stepTime = 20;
    const increment = confVal / (dur / stepTime);
    const counter = setInterval(() => {
      start += increment;
      if (start >= confVal) {
        $("confNumber").textContent = `${confVal.toFixed(1)}%`;
        clearInterval(counter);
      } else {
        $("confNumber").textContent = `${start.toFixed(1)}%`;
      }
    }, stepTime);

    // 3. Supervisor Review
    const reviewIcon = $("reviewIcon");
    const reviewText = $("reviewText");
    if (r.requires_human_review) {
      reviewIcon.innerHTML = `<svg viewBox="0 0 16 16" width="16" height="16" fill="var(--warn)" aria-hidden="true"><path d="M8 1L0.5 14h15L8 1zm0 3l5.5 9.5h-11L8 4zm-.75 3v3.5h1.5V7h-1.5zm0 4.5v1.5h1.5v-1.5h-1.5z"/></svg>`;
      const reason = (r.human_review_reasons && r.human_review_reasons[0]) || "Verification flagged by compliance rules.";
      reviewText.textContent = `Supervisor review required: ${reason}`;
    } else {
      reviewIcon.innerHTML = `<svg viewBox="0 0 16 16" width="16" height="16" fill="var(--pass)" aria-hidden="true"><path d="M13.5 3.5L6 11 2.5 7.5l1.5-1.5L6 8l6-6 1.5 1.5z"/></svg>`;
      reviewText.textContent = "Automated verification passed. No supervisor review required.";
    }

    // 4. Findings (2-col key/value list)
    $("resDefectType").textContent = (r.defect_type || "none").toUpperCase();
    $("resLocation").textContent = r.defect_location || "Not specified";
    $("resComponentId").textContent = r.object_name || "Unassigned";
    $("resInspectionId").textContent = r.inspection_id || "—";
    if ($("resAuditHash")) $("resAuditHash").textContent = r.audit_hash || "Simulated local seal";
    const detLabel = r.detector === "VLMDefectDetector"
      ? `Cloud VLM (${r.detector_model || "OpenRouter"})`
      : r.detector === "FallbackHeuristicDefectDetector"
      ? "Heuristic Fallback (VLM config missing)"
      : (r.detector || "Heuristic Defect Detector");
    if ($("resDetector")) $("resDetector").textContent = detLabel;
    if ($("resDescription")) $("resDescription").textContent = r.defect_description || r.risk_explanation || "No visual description provided.";

    // 5. Clauses (Accordion: rows separated by 1px divider, open row amber left rule 2px)
    const clausesList = $("clausesList");
    clausesList.innerHTML = "";
    if (r.standard_evidence && r.standard_evidence.length > 0) {
      r.standard_evidence.forEach((c, idx) => {
        const isFirst = idx === 0;
        const row = document.createElement("div");
        row.className = `clause-row ${isFirst ? "is-open" : ""}`;
        row.style.setProperty("--i", idx);

        const scoreVal = Number(c.score || 0);
        const scorePct = Math.min(100, Math.max(10, scoreVal * 10));

        row.innerHTML = `
          <div class="clause-header" tabindex="0" role="button" aria-expanded="${isFirst}">
            <div class="clause-title-group">
              <span class="clause-tag">CLAUSE ${escapeHtml(c.clause_id || "REF")}</span>
              <span class="clause-title">${escapeHtml(c.title || "Standard specification")}</span>
            </div>
            <div class="clause-score-group">
              <div class="clause-score-bar">
                <div class="clause-score-fill" style="width: ${scorePct}%;"></div>
              </div>
              <span class="clause-score-val">${scoreVal.toFixed(2)}</span>
            </div>
          </div>
          <div class="clause-body" ${isFirst ? "" : "hidden"}>
            <p>${escapeHtml(c.text)}</p>
          </div>
        `;

        // Hover & open triggers bbox highlight/pulse on hero image
        const header = row.querySelector(".clause-header");
        const body = row.querySelector(".clause-body");

        function highlightBbox(on) {
          const frame = $("imageFrame");
          if (!frame) return;
          if (on) frame.classList.add("bbox-pulsing");
          else frame.classList.remove("bbox-pulsing");
        }

        row.addEventListener("mouseenter", () => highlightBbox(true));
        row.addEventListener("mouseleave", () => highlightBbox(false));

        header.addEventListener("click", () => {
          const isExpanded = !body.hidden;
          body.hidden = isExpanded;
          header.setAttribute("aria-expanded", !isExpanded);
          row.classList.toggle("is-open", !isExpanded);
          highlightBbox(!isExpanded);
        });

        header.addEventListener("keydown", (e) => {
          if (e.key === "Enter" || e.key === " ") {
            e.preventDefault();
            header.click();
          }
        });

        clausesList.appendChild(row);
      });
    } else {
      clausesList.innerHTML = `<p class="sample-sub" style="padding: 8px 0;">No matching standard clauses identified.</p>`;
    }

    // 6. Sensor Telemetry
    const sensorSection = $("sensorSection");
    const sensorList = $("sensorList");
    if (r.sensor_readings && r.sensor_readings.length > 0) {
      sensorSection.hidden = false;
      sensorList.innerHTML = r.sensor_readings
        .map((s) => {
          const val = Number(s.value);
          const nameLower = (s.name || "").toLowerCase();
          let breached = false;
          if (nameLower.includes("temp") && val > 80.0) breached = true;
          if (nameLower.includes("vib") && val > 4.0) breached = true;
          if (nameLower.includes("press") && Math.abs(val) > 5.0) breached = true;

          return `
            <div class="sensor-item">
              <span class="sensor-name">${escapeHtml(s.name)}</span>
              <span class="sensor-val ${breached ? "sensor-breach" : ""}">${escapeHtml(s.value)} ${escapeHtml(s.unit || "")} ${breached ? "[BREACH]" : ""}</span>
            </div>`;
        })
        .join("");
    } else {
      sensorSection.hidden = true;
    }

    // 7. Decision Rationale
    $("rationaleText").textContent = r.risk_explanation;

    // Left Hero Canvas: Display Bounding Box with single flush label chip
    const bboxSvg = $("bboxSvg");
    const bboxChip = $("bboxChip");
    const bboxRect = $("bboxRect");

    if (bboxSvg && bboxChip) {
      if (r.defect_bbox && bboxRect) {
        bboxSvg.removeAttribute("hidden");
        bboxChip.hidden = false;
        const defect = (r.defect_type || "Defect").toUpperCase();
        const conf = (r.confidence * 100).toFixed(0);
        $("bboxChipLabel").textContent = `${defect} ${conf}%`;

        const bx = Math.max(0, Math.min(100, r.defect_bbox.x * 100)).toFixed(1);
        const by = Math.max(0, Math.min(100, r.defect_bbox.y * 100)).toFixed(1);
        const bw = Math.max(0, Math.min(100 - bx, r.defect_bbox.width * 100)).toFixed(1);
        const bh = Math.max(0, Math.min(100 - by, r.defect_bbox.height * 100)).toFixed(1);
        bboxRect.setAttribute("x", bx);
        bboxRect.setAttribute("y", by);
        bboxRect.setAttribute("width", bw);
        bboxRect.setAttribute("height", bh);
        bboxChip.style.top = `${by}%`;
        bboxChip.style.left = `${bx}%`;
      } else {
        bboxSvg.setAttribute("hidden", "");
        bboxChip.hidden = true;
      }
    }

    // Button Actions
    const btnCert = $("btnViewCert");
    if (btnCert) {
      btnCert.onclick = () => {
        const base = (window.APP_CONFIG && window.APP_CONFIG.apiBase) || "";
        if (!r.is_simulated_demo && r.inspection_id) {
          window.open(`${base}/api/inspect/${r.inspection_id}/certificate`, "_blank");
        } else {
          showToast("Opening ISO 9001 compliance certificate...", false);
          window.print();
        }
      };
    }

    $("btnDownloadJson").onclick = () => {
      const blob = new Blob([JSON.stringify(r, null, 2)], { type: "application/json" });
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `inspection_${r.inspection_id}.json`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
    };

    const btnCopy = $("btnCopyJson");
    if (btnCopy) {
      btnCopy.onclick = async () => {
        try {
          await navigator.clipboard.writeText(JSON.stringify(r, null, 2));
          showToast("Inspection JSON copied to clipboard.", false);
        } catch {
          showToast("Failed to copy JSON to clipboard.", true);
        }
      };
    }

    $("btnPrintPdf").onclick = () => window.print();

    $("btnNewInspection").onclick = resetWorkspace;
  }

  function resetWorkspace() {
    state.currentReport = null;
    state.annotatedUrl = null;
    state.visionHints = null;

    $("flowResult").hidden = true;
    $("flowForm").hidden = false;
    $("pipelineLoader").hidden = true;

    const demoBanner = $("demoBanner");
    if (demoBanner) demoBanner.hidden = true;

    const frame = $("imageFrame");
    if (frame) {
      frame.classList.remove("is-zoomed");
      $("btnZoomFit")?.classList.add("is-active");
      $("btnZoomActual")?.classList.remove("is-active");
    }

    const clauseBtn = $("btnToggleAllClauses");
    if (clauseBtn) clauseBtn.textContent = "Expand all";

    $("btnRemoveImage").click();
    $("btnRemoveSensor").click();
    $("objectNameInput").value = "";
    $("standardSelect").value = "builtin";
    $("customDocBox").hidden = true;

    updateHeroCanvas();
    goToStep(1);
  }

  // ==========================================================================
  // Interactive Stepper Navigation
  // ==========================================================================
  function initStepper() {
    [1, 2, 3].forEach((n) => {
      const lbl = $(`step${n}Label`);
      if (!lbl) return;
      lbl.addEventListener("click", () => {
        if (n === 1 || state.imageFile || n <= state.step) {
          goToStep(n);
        } else {
          showToast("Upload an inspection defect photo first.", true);
        }
      });
    });
  }

  // ==========================================================================
  // Optical Stage Toolbar (Fit vs 1:1, Bounding Box Overlay Toggle)
  // ==========================================================================
  function initStageToolbar() {
    const btnFit = $("btnZoomFit");
    const btnActual = $("btnZoomActual");
    const btnBbox = $("btnToggleBbox");
    const frame = $("imageFrame");
    const bboxSvg = $("bboxSvg");
    const bboxChip = $("bboxChip");

    if (btnFit && btnActual && frame) {
      btnFit.addEventListener("click", () => {
        frame.classList.remove("is-zoomed");
        btnFit.classList.add("is-active");
        btnActual.classList.remove("is-active");
      });

      btnActual.addEventListener("click", () => {
        frame.classList.add("is-zoomed");
        btnActual.classList.add("is-active");
        btnFit.classList.remove("is-active");
      });
    }

    if (btnBbox && bboxSvg && bboxChip) {
      btnBbox.addEventListener("click", () => {
        const isHidden = bboxSvg.hasAttribute("hidden");
        if (isHidden) {
          bboxSvg.removeAttribute("hidden");
          bboxChip.hidden = false;
          btnBbox.classList.add("is-active");
        } else {
          bboxSvg.setAttribute("hidden", "");
          bboxChip.hidden = true;
          btnBbox.classList.remove("is-active");
        }
      });
    }
  }

  // ==========================================================================
  // Clauses Expand / Collapse All Toggle
  // ==========================================================================
  function initClauseToggle() {
    const btn = $("btnToggleAllClauses");
    if (!btn) return;

    btn.addEventListener("click", () => {
      const rows = document.querySelectorAll(".clause-row");
      const anyClosed = Array.from(rows).some((r) => {
        const body = r.querySelector(".clause-body");
        return body && body.hidden;
      });

      rows.forEach((r) => {
        const header = r.querySelector(".clause-header");
        const body = r.querySelector(".clause-body");
        if (body && header) {
          body.hidden = !anyClosed;
          header.setAttribute("aria-expanded", anyClosed);
          r.classList.toggle("is-open", anyClosed);
        }
      });

      btn.textContent = anyClosed ? "Collapse all" : "Expand all";
    });
  }

  // ==========================================================================
  // Backend Agent Service Health Ping
  // ==========================================================================
  async function checkBackendHealth() {
    const pill = $("apiStatusPill");
    const dot = $("statusDot");
    const lbl = $("statusLabel");
    if (!pill || !dot || !lbl) return;

    const base = getApiBase();
    const displayHost = base || (typeof window !== "undefined" && window.location.origin) || "localhost:8000";
    try {
      const controller = new AbortController();
      const tid = setTimeout(() => controller.abort(), 2000);
      const res = await fetch(`${base}/health`, { signal: controller.signal });
      clearTimeout(tid);
      if (res.ok) {
        const data = await res.json().catch(() => ({}));
        dot.className = "status-dot is-online";
        if (data.detector === "vlm") {
          if (data.vlm_configured) {
            lbl.textContent = `Agent (VLM Cloud Active)`;
            pill.title = `Backend online using OpenRouter model: ${data.vlm_model}`;
          } else {
            lbl.textContent = `Agent (Missing VLM API Key)`;
            pill.title = `INSPECTION_VLM_API_KEY is unset or placeholder. Falling back to heuristic.`;
          }
        } else {
          lbl.textContent = `Agent (${data.detector || "connected"})`;
          pill.title = `Backend server online at ${displayHost}`;
        }
        return;
      }
    } catch {
      // offline
    }
    dot.className = "status-dot is-offline";
    lbl.textContent = "Offline (Demo ready)";
    pill.title = `Backend server offline at ${displayHost}. Demonstrations will execute in simulation mode.`;
  }

  // ==========================================================================
  // Keyboard Shortcuts (1, 2, 3 step jump; Escape to exit zoom)
  // ==========================================================================
  function initKeyboardShortcuts() {
    window.addEventListener("keydown", (e) => {
      if (["INPUT", "SELECT", "TEXTAREA"].includes(document.activeElement?.tagName)) {
        return;
      }

      if (e.key === "1") {
        goToStep(1);
      } else if (e.key === "2") {
        if (state.imageFile) goToStep(2);
      } else if (e.key === "3") {
        if (state.imageFile) goToStep(3);
      } else if (e.key === "Escape") {
        const frame = $("imageFrame");
        if (frame && frame.classList.contains("is-zoomed")) {
          $("btnZoomFit")?.click();
        }
      }
    });
  }

  // ==========================================================================
  // App Bootstrapping
  // ==========================================================================
  function init() {
    initStep1();
    initStep2();
    initStep3();
    initStepper();
    initStageToolbar();
    initClauseToggle();
    initKeyboardShortcuts();
    checkBackendHealth();
    goToStep(1);
    updateHeroCanvas();
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }
})();
