import { loadProject, saveProject } from "./api.js";
import { renderPlan } from "./rendering.js";
import { createEditorState } from "./state.js";

const root = document.querySelector("[data-editor-root]");

if (root) {
  const elements = {
    image: root.querySelector("[data-plan-image]"),
    overlay: root.querySelector("[data-plan-overlay]"),
    stage: root.querySelector("[data-plan-stage]"),
    panel: root.querySelector("[data-plan-panel]"),
    hint: root.querySelector("[data-plan-hint]"),
    saveState: root.querySelector("[data-save-state]"),
    notes: root.querySelector("[data-project-notes]"),
    noteCount: root.querySelector("[data-note-count]"),
    cameraCount: root.querySelector("[data-camera-count]"),
    fov: root.querySelector("[data-camera-fov]"),
    undo: root.querySelector("[data-undo]"),
    deleteSelection: root.querySelector("[data-delete-selection]"),
    tools: [...root.querySelectorAll("[data-tool]")],
  };

  const FIRST_RETRY_MS = 1_000;
  const MAX_RETRY_MS = 15_000;
  const ADJUST_THRESHOLD_PX = 4;
  const MIN_ZOOM = 1;
  const MAX_ZOOM = 8;

  const documentUrl = root.dataset.documentUrl;
  let state;
  let revision;
  let dimensions;
  let activeTool = "select";
  let draft = null;
  let adjust = null;
  let pan = null;
  let zoom = 1;
  let baseWidth = 0;
  let saveTimer = null;
  let saveQueue = Promise.resolve();
  let changeVersion = 0;
  let savedVersion = 0;
  let retryDelay = 0;
  let csrfRefreshed = false;

  function setSaveState(message, variant = "") {
    elements.saveState.textContent = message;
    elements.saveState.className = `save-state${variant ? ` is-${variant}` : ""}`;
  }

  function updateControls() {
    elements.undo.disabled = !state?.canUndo();
    elements.deleteSelection.disabled = !state?.selectedId();
    elements.cameraCount.textContent = state ? state.cameraCount() : "0";
    elements.noteCount.textContent = `${elements.notes.value.length} / 5000`;
  }

  function render() {
    if (!state || !dimensions) return;
    renderPlan(elements.overlay, state.itemsWith(draft), dimensions, state.selectedId());
    updateControls();
  }

  function scheduleRetry(delay) {
    clearTimeout(saveTimer);
    saveTimer = window.setTimeout(saveNow, delay);
  }

  async function refreshCsrfToken() {
    const meta = document.querySelector('meta[name="csrf-token"]');
    if (!meta) return false;
    const response = await fetch(window.location.href, {
      headers: { Accept: "text/html" },
      cache: "no-store",
    });
    if (!response.ok) return false;
    const fresh = new DOMParser()
      .parseFromString(await response.text(), "text/html")
      .querySelector('meta[name="csrf-token"]')?.content;
    if (!fresh) return false;
    meta.content = fresh;
    return true;
  }

  async function handleSaveFailure(error) {
    // Someone saved this plan from another tab or device. The markup on this screen is
    // what the person is actually looking at, so take the server's revision and push
    // again instead of stranding every edit made from here on.
    if (error.status === 409 && typeof error.payload?.revision === "number") {
      revision = error.payload.revision;
      setSaveState("Catching up…");
      scheduleRetry(200);
      return;
    }
    // Restarting the server mints a new secret key, which quietly invalidates the
    // session holding the CSRF token. Fetch a fresh one rather than lose the work.
    if (error.status === 400 && !csrfRefreshed && (await refreshCsrfToken())) {
      csrfRefreshed = true;
      setSaveState("Reconnecting…");
      scheduleRetry(200);
      return;
    }
    if (error.status === 400 || error.status === 404) {
      setSaveState(error.message, "error");
      return;
    }
    retryDelay = Math.min(retryDelay ? retryDelay * 2 : FIRST_RETRY_MS, MAX_RETRY_MS);
    setSaveState(`Not saved — retrying in ${Math.round(retryDelay / 1000)}s`, "error");
    scheduleRetry(retryDelay);
  }

  function saveNow() {
    clearTimeout(saveTimer);
    if (!state || savedVersion === changeVersion) return saveQueue;
    saveQueue = saveQueue
      .then(async () => {
        if (savedVersion === changeVersion) return;
        const savingVersion = changeVersion;
        setSaveState("Saving…");
        const result = await saveProject(
          documentUrl,
          {
            revision,
            document: state.document(),
            notes: elements.notes.value,
          },
        );
        revision = result.revision;
        savedVersion = Math.max(savedVersion, savingVersion);
        retryDelay = 0;
        csrfRefreshed = false;
        setSaveState(
          savedVersion === changeVersion ? "All changes saved" : "Unsaved changes",
          savedVersion === changeVersion ? "saved" : "",
        );
      })
      .catch((error) => {
        if (error.name !== "AbortError") return handleSaveFailure(error);
      });
    return saveQueue;
  }

  function markChanged() {
    changeVersion += 1;
    setSaveState("Unsaved changes");
    clearTimeout(saveTimer);
    saveTimer = window.setTimeout(saveNow, 650);
  }

  function setTool(tool) {
    activeTool = tool;
    for (const button of elements.tools) {
      const active = button.dataset.tool === tool;
      button.classList.toggle("is-active", active);
      button.setAttribute("aria-pressed", String(active));
    }
    elements.hint.textContent =
      tool === "camera"
        ? "Click for a standard camera cone, or drag to set direction and reach."
        : "Tap a camera to select it. Drag inside its cone to aim it and set how far it reaches.";
    elements.overlay.style.cursor = tool === "camera" ? "crosshair" : "grab";
  }

  function pointFromEvent(event) {
    const bounds = elements.overlay.getBoundingClientRect();
    return {
      x: ((event.clientX - bounds.left) / bounds.width) * dimensions.width,
      y: ((event.clientY - bounds.top) / bounds.height) * dimensions.height,
    };
  }

  function applyZoom(nextZoom, anchor) {
    const clamped = Math.min(MAX_ZOOM, Math.max(MIN_ZOOM, nextZoom));
    if (!baseWidth || clamped === zoom) return;
    // Keep whatever sits under the cursor pinned there as the stage grows or shrinks.
    const before = elements.stage.getBoundingClientRect();
    const ratioX = before.width ? (anchor.x - before.left) / before.width : 0.5;
    const ratioY = before.height ? (anchor.y - before.top) / before.height : 0.5;

    zoom = clamped;
    elements.stage.classList.toggle("is-zoomed", zoom !== 1);
    elements.stage.style.width = zoom === 1 ? "" : `${baseWidth * zoom}px`;

    const after = elements.stage.getBoundingClientRect();
    elements.panel.scrollLeft += after.left + ratioX * after.width - anchor.x;
    elements.panel.scrollTop += after.top + ratioY * after.height - anchor.y;
  }

  function onWheel(event) {
    if (!dimensions) return;
    event.preventDefault();
    // Normalise line and page scrolling to pixels so every input device steps evenly.
    const lines = event.deltaMode === 1 ? 16 : event.deltaMode === 2 ? 400 : 1;
    const factor = Math.exp((-event.deltaY * lines) / 650);
    applyZoom(zoom * factor, { x: event.clientX, y: event.clientY });
  }

  function rangeFromDistance(distance) {
    return Math.min(2, Math.max(0.03, distance / Math.min(dimensions.width, dimensions.height)));
  }

  function cameraFromPoint(point) {
    const cameraNumber = state.document().items.length + 1;
    return {
      id: crypto.randomUUID(),
      type: "camera",
      x: point.x / dimensions.width,
      y: point.y / dimensions.height,
      direction_degrees: -90,
      fov_degrees: Number(elements.fov.value),
      range: 0.16,
      label: `C${String(cameraNumber).padStart(2, "0")}`,
      note: "",
    };
  }

  function capturePointer(pointerId) {
    try {
      elements.overlay.setPointerCapture(pointerId);
    } catch {
      // The pointer was already released; the gesture still tracks without capture.
    }
  }

  function releasePointer(pointerId) {
    try {
      elements.overlay.releasePointerCapture(pointerId);
    } catch {
      // Already released, e.g. the browser cancelled the gesture first.
    }
  }

  function beginPan(event) {
    pan = {
      clientX: event.clientX,
      clientY: event.clientY,
      scrollLeft: elements.panel.scrollLeft,
      scrollTop: elements.panel.scrollTop,
    };
    capturePointer(event.pointerId);
    elements.overlay.style.cursor = "grabbing";
  }

  function onPointerDown(event) {
    if (!state) return;
    // Middle drag pans from anywhere, including over a camera, in any tool.
    if (event.button === 1) {
      event.preventDefault();
      beginPan(event);
      return;
    }
    const item = event.target.closest?.("[data-item-id]");
    if (activeTool === "select") {
      const itemId = item?.dataset.itemId ?? null;
      state.select(itemId);
      const camera = itemId ? state.itemById(itemId) : null;
      if (camera) {
        // Hold anywhere in the cone and drag: around to aim, in and out for reach.
        adjust = {
          id: itemId,
          originX: camera.x * dimensions.width,
          originY: camera.y * dimensions.height,
          clientX: event.clientX,
          clientY: event.clientY,
          started: false,
        };
        capturePointer(event.pointerId);
      } else {
        // Empty canvas: drag to pan, which is also how touch gets around when zoomed in.
        beginPan(event);
      }
      render();
      return;
    }
    if (activeTool !== "camera" || item) return;
    const point = pointFromEvent(event);
    draft = cameraFromPoint(point);
    draft.startX = point.x;
    draft.startY = point.y;
    capturePointer(event.pointerId);
    render();
  }

  function onPointerMove(event) {
    if (pan) {
      elements.panel.scrollLeft = pan.scrollLeft - (event.clientX - pan.clientX);
      elements.panel.scrollTop = pan.scrollTop - (event.clientY - pan.clientY);
      return;
    }
    if (adjust) {
      const travelled = Math.hypot(event.clientX - adjust.clientX, event.clientY - adjust.clientY);
      if (!adjust.started && travelled < ADJUST_THRESHOLD_PX) return;
      if (!adjust.started) {
        // Checkpoint once per drag, not once per frame, so undo steps back the whole move.
        state.beginChange();
        adjust.started = true;
      }
      const point = pointFromEvent(event);
      const dx = point.x - adjust.originX;
      const dy = point.y - adjust.originY;
      const distance = Math.hypot(dx, dy);
      if (distance > 1) {
        state.updateItem(adjust.id, {
          direction_degrees: (Math.atan2(dy, dx) * 180) / Math.PI,
          range: rangeFromDistance(distance),
        });
        render();
      }
      return;
    }
    if (!draft) return;
    const point = pointFromEvent(event);
    const dx = point.x - draft.startX;
    const dy = point.y - draft.startY;
    const distance = Math.hypot(dx, dy);
    if (distance > 4) {
      draft.direction_degrees = (Math.atan2(dy, dx) * 180) / Math.PI;
      draft.range = rangeFromDistance(distance);
    }
    render();
  }

  function onPointerUp(event) {
    if (pan) {
      pan = null;
      releasePointer(event.pointerId);
      elements.overlay.style.cursor = activeTool === "camera" ? "crosshair" : "grab";
      return;
    }
    if (adjust) {
      const changed = adjust.started;
      adjust = null;
      releasePointer(event.pointerId);
      if (changed) {
        render();
        markChanged();
      }
      return;
    }
    if (!draft) return;
    const completed = { ...draft };
    delete completed.startX;
    delete completed.startY;
    state.addCamera(completed);
    draft = null;
    releasePointer(event.pointerId);
    setTool("select");
    render();
    markChanged();
  }

  async function initialize() {
    try {
      const [payload] = await Promise.all([
        loadProject(documentUrl),
        elements.image.decode(),
      ]);
      dimensions = {
        width: elements.image.naturalWidth,
        height: elements.image.naturalHeight,
      };
      elements.overlay.setAttribute("viewBox", `0 0 ${dimensions.width} ${dimensions.height}`);
      baseWidth = elements.image.getBoundingClientRect().width;
      state = createEditorState(payload.document);
      revision = payload.revision;
      elements.notes.value = payload.project.notes;
      setSaveState("All changes saved", "saved");
      render();
    } catch (error) {
      if (error.name !== "AbortError") setSaveState(error.message, "error");
    }
  }

  for (const button of elements.tools) {
    button.addEventListener("click", () => setTool(button.dataset.tool));
  }
  elements.overlay.addEventListener("pointerdown", onPointerDown);
  elements.overlay.addEventListener("pointermove", onPointerMove);
  elements.overlay.addEventListener("pointerup", onPointerUp);
  elements.overlay.addEventListener("pointercancel", () => {
    const adjusted = adjust?.started;
    draft = null;
    adjust = null;
    pan = null;
    render();
    // The cone was already moved before the gesture was cancelled, so persist it.
    if (adjusted) markChanged();
  });
  elements.panel.addEventListener("wheel", onWheel, { passive: false });
  // Suppress the Windows middle-click autoscroll ring so the pan gesture owns the button.
  elements.overlay.addEventListener("auxclick", (event) => {
    if (event.button === 1) event.preventDefault();
  });
  elements.overlay.addEventListener("dblclick", (event) => {
    if (activeTool !== "select" || event.target.closest?.("[data-item-id]")) return;
    applyZoom(1, { x: event.clientX, y: event.clientY });
  });
  window.addEventListener("resize", () => {
    // The fit width follows the panel, so re-measure it whenever we are back at fit.
    if (zoom === 1) baseWidth = elements.image.getBoundingClientRect().width;
  });
  elements.notes.addEventListener("input", () => {
    updateControls();
    markChanged();
  });
  elements.undo.addEventListener("click", () => {
    if (state.undo()) {
      render();
      markChanged();
    }
  });
  elements.deleteSelection.addEventListener("click", () => {
    if (state.deleteSelected()) {
      render();
      markChanged();
    }
  });
  document.addEventListener("visibilitychange", () => {
    if (document.hidden && savedVersion !== changeVersion) saveNow();
  });
  window.addEventListener("beforeunload", (event) => {
    if (savedVersion === changeVersion) return;
    event.preventDefault();
    event.returnValue = "";
  });
  window.addEventListener("pagehide", saveNow);

  initialize();
}
