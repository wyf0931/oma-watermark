(() => {
  "use strict";

  const MAX_FILE_BYTES = 25 * 1024 * 1024;
  const MIN_ROI_SIZE = 4;

  const elements = {
    dropzone: document.querySelector("#dropzone"),
    emptyState: document.querySelector("#emptyState"),
    editor: document.querySelector("#editor"),
    imageWrap: document.querySelector("#imageWrap"),
    image: document.querySelector("#image"),
    imageMeta: document.querySelector("#imageMeta"),
    viewHint: document.querySelector("#viewHint"),
    selectionBox: document.querySelector("#selectionBox"),
    selectionLabel: document.querySelector("#selectionLabel"),
    drawLayer: document.querySelector("#drawLayer"),
    fileInput: document.querySelector("#fileInput"),
    replaceButton: document.querySelector("#replaceButton"),
    originalTab: document.querySelector("#originalTab"),
    resultTab: document.querySelector("#resultTab"),
    maskTab: document.querySelector("#maskTab"),
    roiText: document.querySelector("#roiText"),
    clearSelectionButton: document.querySelector("#clearSelectionButton"),
    modeSelect: document.querySelector("#modeSelect"),
    aiHint: document.querySelector("#aiHint"),
    thresholdInput: document.querySelector("#thresholdInput"),
    thresholdValue: document.querySelector("#thresholdValue"),
    expandInput: document.querySelector("#expandInput"),
    expandValue: document.querySelector("#expandValue"),
    processButton: document.querySelector("#processButton"),
    processSpinner: document.querySelector("#processSpinner"),
    processLabel: document.querySelector("#processLabel"),
    status: document.querySelector("#status"),
    downloadLink: document.querySelector("#downloadLink"),
  };

  const state = {
    file: null,
    originalUrl: null,
    resultUrl: null,
    maskUrl: null,
    resultFilename: null,
    imageWidth: 0,
    imageHeight: 0,
    roi: null,
    view: "original",
    drag: null,
    loading: false,
    aiAvailable: false,
    aiStatusLoaded: false,
    requestId: 0,
  };

  const viewHints = {
    original: "在原图上拖动，框住水印文字",
    result: "处理结果：可切换原图对比，或下载图片",
    mask: "红色区域是本次检测到并修复的像素",
  };

  function showStatus(message, kind) {
    elements.status.hidden = false;
    elements.status.className = `alert alert-${kind} alert-soft text-sm`;
    elements.status.textContent = message;
  }

  function hideStatus() {
    elements.status.hidden = true;
  }

  function updateAiHint() {
    if (!state.aiStatusLoaded) {
      elements.aiHint.textContent = "正在检测 AI 模型…";
    } else if (state.aiAvailable) {
      elements.aiHint.textContent = "AI 模型已就绪，首次推理会稍慢。";
    } else if (elements.modeSelect.value === "ai") {
      elements.aiHint.textContent =
        "未找到 AI 模型。请运行 uv run oma-watermark-download-model。";
    } else {
      elements.aiHint.textContent = "AI 精修可选，首次使用需下载约 93 MB 模型。";
    }
  }

  async function refreshAiStatus() {
    try {
      const response = await fetch("/api/health");
      const payload = await response.json();
      state.aiAvailable = Boolean(payload.ai_available);
    } catch {
      state.aiAvailable = false;
    }
    state.aiStatusLoaded = true;
    updateAiHint();
    updateControls();
  }

  function setTabEnabled(tab, enabled) {
    tab.disabled = !enabled;
    tab.classList.toggle("tab-disabled", !enabled);
  }

  function setView(view) {
    const urls = {
      original: state.originalUrl,
      result: state.resultUrl,
      mask: state.maskUrl,
    };
    if (!urls[view]) return;

    state.view = view;
    const tab = {
      original: elements.originalTab,
      result: elements.resultTab,
      mask: elements.maskTab,
    }[view];
    tab.checked = true;

    elements.image.src = urls[view];
    elements.imageWrap.dataset.view = view;
    elements.drawLayer.hidden = view !== "original";
    elements.viewHint.textContent = viewHints[view];
    renderSelection();
  }

  function renderSelection() {
    const roi = state.roi;
    const visible =
      state.view === "original" &&
      roi &&
      roi.width >= 2 &&
      roi.height >= 2 &&
      state.imageWidth > 0;

    if (!visible) {
      elements.selectionBox.hidden = true;
      return;
    }

    elements.selectionBox.hidden = false;
    elements.selectionBox.style.left = `${(roi.x / state.imageWidth) * 100}%`;
    elements.selectionBox.style.top = `${(roi.y / state.imageHeight) * 100}%`;
    elements.selectionBox.style.width = `${(roi.width / state.imageWidth) * 100}%`;
    elements.selectionBox.style.height = `${(roi.height / state.imageHeight) * 100}%`;
    elements.selectionLabel.textContent = `${roi.width} × ${roi.height}`;
  }

  function updateMeta() {
    if (!state.file || !state.imageWidth) {
      elements.imageMeta.textContent = "";
      return;
    }
    elements.imageMeta.textContent = `${state.file.name} · ${state.imageWidth} × ${state.imageHeight} px`;
  }

  function updateControls() {
    const hasRoi =
      state.roi &&
      state.roi.width >= MIN_ROI_SIZE &&
      state.roi.height >= MIN_ROI_SIZE;

    const aiUnavailable =
      elements.modeSelect.value === "ai" &&
      state.aiStatusLoaded &&
      !state.aiAvailable;

    elements.processButton.disabled =
      state.loading || !state.file || !hasRoi || aiUnavailable;
    elements.clearSelectionButton.disabled = state.loading || !hasRoi;
    elements.replaceButton.disabled = state.loading || !state.file;
    elements.fileInput.disabled = state.loading;
    elements.modeSelect.disabled = state.loading;
    elements.thresholdInput.disabled = state.loading;
    elements.expandInput.disabled = state.loading;
    elements.thresholdValue.value = elements.thresholdInput.value;
    elements.thresholdValue.textContent = elements.thresholdInput.value;
    elements.expandValue.value = elements.expandInput.value;
    elements.expandValue.textContent = `${elements.expandInput.value} px`;
    elements.processSpinner.hidden = !state.loading;
    let processLabel = state.resultUrl ? "重新处理" : "祛除水印";
    if (state.loading) {
      processLabel = elements.modeSelect.value === "ai" ? "AI 精修中…" : "正在修复…";
    }
    elements.processLabel.textContent = processLabel;
    updateAiHint();

    elements.roiText.textContent = hasRoi
      ? `${state.roi.x}, ${state.roi.y} · ${state.roi.width} × ${state.roi.height}`
      : "尚未框选";

    elements.downloadLink.hidden = !state.resultUrl;
    updateMeta();
  }

  function resetResult() {
    state.resultUrl = null;
    state.maskUrl = null;
    state.resultFilename = null;
    setTabEnabled(elements.resultTab, false);
    setTabEnabled(elements.maskTab, false);
    elements.resultTab.checked = false;
    elements.maskTab.checked = false;
    elements.downloadLink.hidden = true;
    elements.downloadLink.removeAttribute("href");
  }

  function showEmptyState() {
    elements.emptyState.classList.remove("hidden");
    elements.editor.classList.add("hidden");
    elements.replaceButton.disabled = true;
  }

  function clearFileState() {
    state.requestId += 1;
    state.file = null;
    state.imageWidth = 0;
    state.imageHeight = 0;
    state.roi = null;
    state.drag = null;
    state.loading = false;
    state.view = "original";
    resetResult();
    if (state.originalUrl) {
      URL.revokeObjectURL(state.originalUrl);
      state.originalUrl = null;
    }
    elements.image.removeAttribute("src");
    elements.selectionBox.hidden = true;
    elements.fileInput.value = "";
    hideStatus();
    showEmptyState();
    updateControls();
  }

  function loadFile(file) {
    if (!file) return;
    const looksLikeImage =
      file.type.startsWith("image/") || /\.(png|jpe?g|webp|bmp)$/i.test(file.name);
    if (!looksLikeImage) {
      showStatus("请选择 PNG、JPEG、WebP 或 BMP 图片。", "error");
      return;
    }
    if (file.size === 0) {
      showStatus("这个文件是空的，请换一张图片。", "error");
      return;
    }
    if (file.size > MAX_FILE_BYTES) {
      showStatus("图片不能超过 25 MB。", "error");
      return;
    }

    state.requestId += 1;
    if (state.originalUrl) URL.revokeObjectURL(state.originalUrl);

    state.file = file;
    state.originalUrl = URL.createObjectURL(file);
    state.imageWidth = 0;
    state.imageHeight = 0;
    state.roi = null;
    state.drag = null;
    state.loading = false;
    state.view = "original";
    resetResult();
    hideStatus();
    elements.originalTab.checked = true;
    elements.resultTab.checked = false;
    elements.maskTab.checked = false;
    elements.imageWrap.dataset.view = "original";
    elements.drawLayer.hidden = false;
    elements.selectionBox.hidden = true;
    elements.viewHint.textContent = viewHints.original;
    elements.fileInput.value = "";

    elements.image.onload = () => {
      elements.image.onload = null;
      elements.image.onerror = null;
      state.imageWidth = elements.image.naturalWidth;
      state.imageHeight = elements.image.naturalHeight;
      elements.emptyState.classList.add("hidden");
      elements.editor.classList.remove("hidden");
      setView("original");
      updateControls();
    };
    elements.image.onerror = () => {
      elements.image.onload = null;
      elements.image.onerror = null;
      clearFileState();
      showStatus("图片加载失败，请换一张图片。", "error");
    };
    elements.image.src = state.originalUrl;
  }

  function pointInImage(event) {
    const rect = elements.image.getBoundingClientRect();
    const x = ((event.clientX - rect.left) / rect.width) * state.imageWidth;
    const y = ((event.clientY - rect.top) / rect.height) * state.imageHeight;
    return {
      x: Math.max(0, Math.min(state.imageWidth, Math.round(x))),
      y: Math.max(0, Math.min(state.imageHeight, Math.round(y))),
    };
  }

  function rectFromPoints(start, end) {
    const x1 = Math.min(start.x, end.x);
    const y1 = Math.min(start.y, end.y);
    const x2 = Math.max(start.x, end.x);
    const y2 = Math.max(start.y, end.y);
    return { x: x1, y: y1, width: x2 - x1, height: y2 - y1 };
  }

  function finishDrag() {
    if (!state.drag) return;
    state.drag = null;
    if (
      !state.roi ||
      state.roi.width < MIN_ROI_SIZE ||
      state.roi.height < MIN_ROI_SIZE
    ) {
      state.roi = null;
    }
    renderSelection();
    updateControls();
  }

  elements.drawLayer.addEventListener("pointerdown", (event) => {
    if (state.loading || state.view !== "original" || !state.imageWidth) return;
    if (event.button !== 0) return;
    event.preventDefault();

    const start = pointInImage(event);
    state.drag = { start, pointerId: event.pointerId };
    state.roi = { x: start.x, y: start.y, width: 0, height: 0 };
    elements.drawLayer.setPointerCapture(event.pointerId);
    renderSelection();
    updateControls();
  });

  elements.drawLayer.addEventListener("pointermove", (event) => {
    if (!state.drag || state.drag.pointerId !== event.pointerId) return;
    event.preventDefault();
    state.roi = rectFromPoints(state.drag.start, pointInImage(event));
    renderSelection();
    updateControls();
  });

  elements.drawLayer.addEventListener("pointerup", (event) => {
    if (!state.drag || state.drag.pointerId !== event.pointerId) return;
    state.roi = rectFromPoints(state.drag.start, pointInImage(event));
    finishDrag();
  });

  elements.drawLayer.addEventListener("pointercancel", () => {
    state.roi = null;
    finishDrag();
  });

  document.querySelectorAll('input[name="preview-view"]').forEach((tab) => {
    tab.addEventListener("change", (event) => {
      if (event.target.checked) setView(event.target.value);
    });
  });

  elements.fileInput.addEventListener("change", (event) => {
    const file = event.target.files?.[0];
    if (file) loadFile(file);
    event.target.value = "";
  });

  elements.replaceButton.addEventListener("click", () => {
    elements.fileInput.click();
  });

  elements.clearSelectionButton.addEventListener("click", () => {
    state.roi = null;
    state.drag = null;
    if (state.view !== "original") setView("original");
    renderSelection();
    updateControls();
  });

  elements.modeSelect.addEventListener("change", () => {
    if (elements.modeSelect.value === "ai" && !state.aiAvailable) {
      refreshAiStatus();
    } else {
      updateAiHint();
      updateControls();
    }
    if (state.resultUrl) {
      showStatus("修复模式已切换，点击“重新处理”查看新结果。", "info");
    }
  });

  elements.thresholdInput.addEventListener("input", () => {
    elements.thresholdValue.textContent = elements.thresholdInput.value;
    if (state.resultUrl) {
      showStatus("阈值已调整，点击“重新处理”查看新结果。", "info");
    }
  });

  elements.expandInput.addEventListener("input", () => {
    elements.expandValue.textContent = `${elements.expandInput.value} px`;
    if (state.resultUrl) {
      showStatus("边缘扩展已调整，点击“重新处理”查看新结果。", "info");
    }
  });

  elements.processButton.addEventListener("click", async () => {
    if (!state.file || !state.roi || state.loading) return;

    const requestId = ++state.requestId;
    const formData = new FormData();
    formData.append("file", state.file, state.file.name);
    formData.append("x", String(state.roi.x));
    formData.append("y", String(state.roi.y));
    formData.append("width", String(state.roi.width));
    formData.append("height", String(state.roi.height));
    formData.append("threshold", elements.thresholdInput.value);
    formData.append("expand", elements.expandInput.value);
    formData.append("mode", elements.modeSelect.value);

    state.loading = true;
    updateControls();
    hideStatus();

    try {
      const response = await fetch("/api/remove", {
        method: "POST",
        body: formData,
      });
      let payload = null;
      try {
        payload = await response.json();
      } catch {
        throw new Error("服务器返回了无法解析的响应。");
      }
      if (!response.ok) {
        throw new Error(payload?.detail || "处理失败，请稍后重试。");
      }
      if (requestId !== state.requestId) return;

      state.resultUrl = payload.result;
      state.maskUrl = payload.mask_overlay;
      state.resultFilename = payload.filename || "cleaned.png";
      setTabEnabled(elements.resultTab, true);
      setTabEnabled(elements.maskTab, true);
      elements.downloadLink.href = state.resultUrl;
      elements.downloadLink.download = state.resultFilename;
      elements.downloadLink.hidden = false;
      setView("result");
      const prefix = payload.mode === "ai" ? "AI 精修完成" : "完成";
      showStatus(
        `${prefix}：检测并修复了 ${Number(payload.detected_pixels).toLocaleString("zh-CN")} 个水印像素。`,
        "success",
      );
    } catch (error) {
      if (requestId === state.requestId) {
        showStatus(error instanceof Error ? error.message : "处理失败，请稍后重试。", "error");
      }
    } finally {
      if (requestId === state.requestId) {
        state.loading = false;
        updateControls();
      }
    }
  });

  let dragDepth = 0;
  elements.dropzone.addEventListener("dragenter", (event) => {
    event.preventDefault();
    dragDepth += 1;
    elements.dropzone.classList.add("is-dragging");
  });

  elements.dropzone.addEventListener("dragover", (event) => {
    event.preventDefault();
    event.dataTransfer.dropEffect = "copy";
  });

  elements.dropzone.addEventListener("dragleave", (event) => {
    event.preventDefault();
    dragDepth = Math.max(0, dragDepth - 1);
    if (dragDepth === 0) elements.dropzone.classList.remove("is-dragging");
  });

  elements.dropzone.addEventListener("drop", (event) => {
    event.preventDefault();
    dragDepth = 0;
    elements.dropzone.classList.remove("is-dragging");
    if (state.loading) return;
    const file = event.dataTransfer.files?.[0];
    if (file) loadFile(file);
  });

  window.addEventListener("beforeunload", () => {
    if (state.originalUrl) URL.revokeObjectURL(state.originalUrl);
  });

  refreshAiStatus();
  updateControls();
})();
