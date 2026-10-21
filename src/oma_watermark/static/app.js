(() => {
  "use strict";

  const MAX_FILE_BYTES = 25 * 1024 * 1024;
  const MIN_ROI_SIZE = 4;

  const elements = {
    originalPanel: document.querySelector("#originalPanel"),
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
    resultEmpty: document.querySelector("#resultEmpty"),
    resultImageWrap: document.querySelector("#resultImageWrap"),
    resultImage: document.querySelector("#resultImage"),
    resultTabs: document.querySelector("#resultTabs"),
    resultMeta: document.querySelector("#resultMeta"),
    resultHint: document.querySelector("#resultHint"),
    resultTab: document.querySelector("#resultTab"),
    maskTab: document.querySelector("#maskTab"),
    downloadLink: document.querySelector("#downloadLink"),
    fileInput: document.querySelector("#fileInput"),
    openButton: document.querySelector("#openButton"),
    openEmptyButton: document.querySelector("#openEmptyButton"),
    helpButton: document.querySelector("#helpButton"),
    helpDialog: document.querySelector("#helpDialog"),
    clearSelectionIconButton: document.querySelector("#clearSelectionIconButton"),
    processHeaderButton: document.querySelector("#processHeaderButton"),
    startHeaderIcon: document.querySelector("#startHeaderIcon"),
    reprocessHeaderIcon: document.querySelector("#reprocessHeaderIcon"),
    modeSelect: document.querySelector("#modeSelect"),
    aiHint: document.querySelector("#aiHint"),
    aiStatusDot: document.querySelector("#aiStatusDot"),
    thresholdInput: document.querySelector("#thresholdInput"),
    thresholdValue: document.querySelector("#thresholdValue"),
    expandInput: document.querySelector("#expandInput"),
    expandValue: document.querySelector("#expandValue"),
    toastContainer: document.querySelector("#toastContainer"),
    status: document.querySelector("#status"),
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
    drag: null,
    loading: false,
    aiAvailable: false,
    aiStatusLoaded: false,
    modeTouched: false,
    rightView: "result",
    requestId: 0,
    toastTimer: null,
  };

  function showStatus(message, kind = "info", timeout = 4500) {
    window.clearTimeout(state.toastTimer);
    elements.toastContainer.hidden = false;
    elements.status.className = `alert alert-${kind} alert-soft text-sm`;
    elements.status.textContent = message;
    state.toastTimer = window.setTimeout(() => {
      elements.toastContainer.hidden = true;
    }, timeout);
  }

  function hideStatus() {
    window.clearTimeout(state.toastTimer);
    elements.toastContainer.hidden = true;
  }

  function updateAiHint() {
    if (!state.aiStatusLoaded) {
      elements.aiHint.textContent = "正在检测…";
      elements.aiHint.title = "正在检测 AI 模型";
      elements.aiStatusDot.className = "status status-warning";
    } else if (state.aiAvailable) {
      elements.aiHint.textContent = "AI 就绪";
      elements.aiHint.title = "AI 模型已就绪";
      elements.aiStatusDot.className = "status status-success";
    } else {
      elements.aiHint.textContent = "AI 未安装";
      elements.aiHint.title = "AI 模型未安装，可用快速模式";
      elements.aiStatusDot.className = "status status-warning";
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
    if (!state.modeTouched) {
      elements.modeSelect.value = state.aiAvailable ? "ai" : "fast";
    }
    updateControls();
  }

  function updateMeta() {
    if (!state.file || !state.imageWidth) {
      elements.imageMeta.textContent = "";
      return;
    }
    elements.imageMeta.textContent = `${state.file.name} · ${state.imageWidth} × ${state.imageHeight} px`;
  }

  function hasValidRoi() {
    return Boolean(
      state.roi &&
        state.roi.width >= MIN_ROI_SIZE &&
        state.roi.height >= MIN_ROI_SIZE,
    );
  }

  function primaryActionLabel() {
    if (state.loading) return "处理中…";
    return state.resultUrl ? "重新处理" : "开始处理";
  }

  function updateControls() {
    const roiReady = hasValidRoi();
    const aiUnavailable =
      elements.modeSelect.value === "ai" &&
      state.aiStatusLoaded &&
      !state.aiAvailable;
    const canProcess =
      Boolean(state.file) &&
      state.imageWidth > 0 &&
      roiReady &&
      !state.loading &&
      !aiUnavailable;
    const actionLabel = primaryActionLabel();

    elements.processHeaderButton.disabled = !canProcess;
    elements.processHeaderButton.setAttribute("aria-label", actionLabel);
    elements.processHeaderButton.title = actionLabel;
    elements.startHeaderIcon.classList.toggle("hidden", Boolean(state.resultUrl));
    elements.reprocessHeaderIcon.classList.toggle("hidden", !state.resultUrl);
    elements.clearSelectionIconButton.disabled = state.loading || !roiReady;
    elements.openButton.disabled = state.loading;
    elements.openEmptyButton.disabled = state.loading;
    elements.modeSelect.disabled = state.loading;
    elements.thresholdInput.disabled = state.loading;
    elements.expandInput.disabled = state.loading;

    elements.thresholdValue.value = elements.thresholdInput.value;
    elements.thresholdValue.textContent = elements.thresholdInput.value;
    elements.expandValue.value = elements.expandInput.value;
    elements.expandValue.textContent = `${elements.expandInput.value} px`;

    updateAiHint();
    updateMeta();
  }

  function resetResult() {
    state.resultUrl = null;
    state.maskUrl = null;
    state.resultFilename = null;
    state.rightView = "result";
    elements.resultImage.removeAttribute("src");
    elements.resultImageWrap.hidden = true;
    elements.resultEmpty.hidden = false;
    elements.resultTabs.hidden = true;
    elements.resultMeta.textContent = "结果预览";
    elements.resultHint.textContent = "结果仅替换选区像素";
    elements.resultTab.checked = true;
    elements.maskTab.checked = false;
    elements.resultTab.disabled = true;
    elements.maskTab.disabled = true;
    elements.resultTab.classList.add("tab-disabled");
    elements.maskTab.classList.add("tab-disabled");
    elements.downloadLink.removeAttribute("href");
    elements.downloadLink.removeAttribute("download");
    elements.downloadLink.setAttribute("aria-disabled", "true");
    elements.downloadLink.classList.add("btn-disabled");
  }

  function setResultView(view) {
    if (!state.resultUrl) return;
    const nextView = view === "mask" && state.maskUrl ? "mask" : "result";
    state.rightView = nextView;
    elements.resultImage.src = nextView === "mask" ? state.maskUrl : state.resultUrl;
    elements.resultTab.checked = nextView === "result";
    elements.maskTab.checked = nextView === "mask";
  }

  function enableResult(payload) {
    state.resultUrl = payload.result;
    state.maskUrl = payload.mask_overlay;
    state.resultFilename = payload.filename || "cleaned.png";
    elements.resultEmpty.hidden = true;
    elements.resultImageWrap.hidden = false;
    elements.resultTabs.hidden = false;
    elements.resultTab.disabled = false;
    elements.maskTab.disabled = false;
    elements.resultTab.classList.remove("tab-disabled");
    elements.maskTab.classList.remove("tab-disabled");
    const modeLabel = payload.mode === "ai" ? "AI 精修" : "快速模式";
    const pixels = Number(payload.detected_pixels).toLocaleString("zh-CN");
    elements.resultMeta.textContent = `${modeLabel} · 修复 ${pixels} 像素`;
    elements.resultHint.textContent = `${payload.roi.width} × ${payload.roi.height} 选区`;
    elements.viewHint.textContent = "已框选水印区域，点击右上角的刷新按钮";
    setResultView("result");
    elements.downloadLink.href = state.resultUrl;
    elements.downloadLink.download = state.resultFilename;
    elements.downloadLink.setAttribute("aria-disabled", "false");
    elements.downloadLink.classList.remove("btn-disabled");
  }

  function validateFile(file) {
    if (!file) return "没有选择图片。";
    const looksLikeImage =
      file.type.startsWith("image/") || /\.(png|jpe?g|webp|bmp)$/i.test(file.name);
    if (!looksLikeImage) return "请选择 PNG、JPEG、WebP 或 BMP 图片。";
    if (file.size === 0) return "这个文件是空的，请换一张图片。";
    if (file.size > MAX_FILE_BYTES) return "图片不能超过 25 MB。";
    return null;
  }

  function loadFile(file) {
    const validationError = validateFile(file);
    if (validationError) {
      showStatus(validationError, "error", 6000);
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
    resetResult();
    hideStatus();
    elements.fileInput.value = "";
    elements.editor.hidden = true;
    elements.emptyState.hidden = false;
    elements.imageMeta.textContent = "";
    elements.viewHint.textContent = "在原图上拖动，框住水印文字";
    updateControls();

    elements.image.onload = () => {
      elements.image.onload = null;
      elements.image.onerror = null;
      state.imageWidth = elements.image.naturalWidth;
      state.imageHeight = elements.image.naturalHeight;
      elements.emptyState.hidden = true;
      elements.editor.hidden = false;
      renderSelection();
      updateControls();
    };
    elements.image.onerror = () => {
      elements.image.onload = null;
      elements.image.onerror = null;
      state.file = null;
      state.imageWidth = 0;
      state.imageHeight = 0;
      state.roi = null;
      if (state.originalUrl) {
        URL.revokeObjectURL(state.originalUrl);
        state.originalUrl = null;
      }
      elements.image.removeAttribute("src");
      elements.emptyState.hidden = false;
      elements.editor.hidden = true;
      resetResult();
      updateControls();
      showStatus("图片加载失败，请换一张图片。", "error", 6000);
    };
    elements.image.src = state.originalUrl;
  }

  function renderSelection() {
    const roi = state.roi;
    const visible = roi && roi.width >= 2 && roi.height >= 2 && state.imageWidth > 0;
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
    if (!hasValidRoi()) state.roi = null;
    renderSelection();
    updateControls();
    if (state.roi) {
      elements.viewHint.textContent = state.resultUrl
        ? "已框选水印区域，点击右上角的刷新按钮"
        : "已框选水印区域，点击右上角的开始按钮";
    }
  }

  function clearSelection() {
    state.roi = null;
    state.drag = null;
    renderSelection();
    updateControls();
    elements.viewHint.textContent = "在原图上拖动，框住水印文字";
  }

  async function startProcessing() {
    if (!state.file || !hasValidRoi() || state.loading) return;
    if (
      elements.modeSelect.value === "ai" &&
      state.aiStatusLoaded &&
      !state.aiAvailable
    ) {
      showStatus("AI 模型未安装，请切换到快速模式或先下载模型。", "error", 6500);
      return;
    }

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

      enableResult(payload);
      const prefix = payload.mode === "ai" ? "AI 精修完成" : "处理完成";
      showStatus(
        `${prefix}：检测并修复了 ${Number(payload.detected_pixels).toLocaleString("zh-CN")} 个水印像素。`,
        "success",
      );
    } catch (error) {
      if (requestId === state.requestId) {
        showStatus(
          error instanceof Error ? error.message : "处理失败，请稍后重试。",
          "error",
          7000,
        );
      }
    } finally {
      if (requestId === state.requestId) {
        state.loading = false;
        updateControls();
      }
    }
  }

  elements.drawLayer.addEventListener("pointerdown", (event) => {
    if (state.loading || !state.imageWidth) return;
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

  elements.resultTab.addEventListener("change", () => setResultView("result"));
  elements.maskTab.addEventListener("change", () => setResultView("mask"));

  elements.openButton.addEventListener("click", () => elements.fileInput.click());
  elements.openEmptyButton.addEventListener("click", () => elements.fileInput.click());

  elements.fileInput.addEventListener("change", (event) => {
    const file = event.target.files?.[0];
    if (file) loadFile(file);
    event.target.value = "";
  });

  elements.helpButton.addEventListener("click", () => {
    elements.helpDialog.showModal();
  });

  document.addEventListener("keydown", (event) => {
    if (event.key !== "?" || event.metaKey || event.ctrlKey || event.altKey) return;
    const activeTag = document.activeElement?.tagName;
    if (["INPUT", "TEXTAREA", "SELECT"].includes(activeTag)) return;
    event.preventDefault();
    if (!elements.helpDialog.open) elements.helpDialog.showModal();
  });

  elements.clearSelectionIconButton.addEventListener("click", clearSelection);
  elements.processHeaderButton.addEventListener("click", startProcessing);

  elements.downloadLink.addEventListener("click", (event) => {
    if (!elements.downloadLink.getAttribute("href")) event.preventDefault();
  });

  elements.modeSelect.addEventListener("change", () => {
    state.modeTouched = true;
    if (elements.modeSelect.value === "ai" && !state.aiAvailable) {
      refreshAiStatus();
    } else {
      updateControls();
    }
  });

  elements.thresholdInput.addEventListener("input", () => {
    elements.thresholdValue.textContent = elements.thresholdInput.value;
  });

  elements.expandInput.addEventListener("input", () => {
    elements.expandValue.textContent = `${elements.expandInput.value} px`;
  });

  let dragDepth = 0;
  elements.originalPanel.addEventListener("dragenter", (event) => {
    event.preventDefault();
    dragDepth += 1;
    elements.originalPanel.classList.add("is-dragging");
  });

  elements.originalPanel.addEventListener("dragover", (event) => {
    event.preventDefault();
    event.dataTransfer.dropEffect = "copy";
  });

  elements.originalPanel.addEventListener("dragleave", (event) => {
    event.preventDefault();
    dragDepth = Math.max(0, dragDepth - 1);
    if (dragDepth === 0) elements.originalPanel.classList.remove("is-dragging");
  });

  elements.originalPanel.addEventListener("drop", (event) => {
    event.preventDefault();
    dragDepth = 0;
    elements.originalPanel.classList.remove("is-dragging");
    if (state.loading) return;
    const file = event.dataTransfer.files?.[0];
    if (file) loadFile(file);
  });

  window.addEventListener("beforeunload", () => {
    if (state.originalUrl) URL.revokeObjectURL(state.originalUrl);
  });

  updateControls();
  refreshAiStatus();
})();
