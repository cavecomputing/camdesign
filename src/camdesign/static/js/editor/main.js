import { loadProject, saveProject } from "./api.js";
import { renderPlan } from "./rendering.js";
import { createEditorState } from "./state.js";

const root = document.querySelector("[data-editor-root]");

if (root) {
  const elements = {
    image: root.querySelector("[data-plan-image]"),
    overlay: root.querySelector("[data-plan-overlay]"),
    stage: root.querySelector("[data-plan-stage]"),
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

  const documentUrl = root.dataset.documentUrl;
  const controller = new AbortController();
  let state;
  let revision;
  let dimensions;
  let activeTool = "select";
  let draft = null;
  let saveTimer = null;
  let saveQueue = Promise.resolve();

  function setSaveState(message, variant = "") {
    elements.saveState.textContent = message;
    elements.saveState.className = `save-state${variant ? ` is-${variant}` : ""}`;
  }

  function updateControls() {
    elements.undo.disabled = !state?.canUndo();
    elements.deleteSelection.disabled = !state?.selectedId();
    elements.cameraCount.textContent = state
      ? state.document().items.filter((item) => item.type === "camera").length
      : "0";
    elements.noteCount.textContent = `${elements.notes.value.length} / 5000`;
  }

  function render() {
    if (!state || !dimensions) return;
    renderPlan(elements.overlay, state.itemsWith(draft), dimensions, state.selectedId());
    updateControls();
  }

  function saveNow() {
    clearTimeout(saveTimer);
    saveQueue = saveQueue
      .then(async () => {
        setSaveState("Saving…");
        const result = await saveProject(
          documentUrl,
          {
            revision,
            document: state.document(),
            notes: elements.notes.value,
          },
          controller.signal,
        );
        revision = result.revision;
        setSaveState("All changes saved", "saved");
      })
      .catch((error) => {
        if (error.name !== "AbortError") setSaveState(error.message, "error");
      });
  }

  function scheduleSave() {
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
        : "Select a camera to review or remove it.";
    elements.overlay.style.cursor = tool === "camera" ? "crosshair" : "default";
  }

  function pointFromEvent(event) {
    const bounds = elements.overlay.getBoundingClientRect();
    return {
      x: ((event.clientX - bounds.left) / bounds.width) * dimensions.width,
      y: ((event.clientY - bounds.top) / bounds.height) * dimensions.height,
    };
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

  function onPointerDown(event) {
    if (!state) return;
    const item = event.target.closest?.("[data-item-id]");
    if (activeTool === "select") {
      state.select(item?.dataset.itemId ?? null);
      render();
      return;
    }
    if (activeTool !== "camera" || item) return;
    const point = pointFromEvent(event);
    draft = cameraFromPoint(point);
    draft.startX = point.x;
    draft.startY = point.y;
    elements.overlay.setPointerCapture(event.pointerId);
    render();
  }

  function onPointerMove(event) {
    if (!draft) return;
    const point = pointFromEvent(event);
    const dx = point.x - draft.startX;
    const dy = point.y - draft.startY;
    const distance = Math.hypot(dx, dy);
    if (distance > 4) {
      draft.direction_degrees = (Math.atan2(dy, dx) * 180) / Math.PI;
      draft.range = Math.min(2, Math.max(0.03, distance / Math.min(dimensions.width, dimensions.height)));
    }
    render();
  }

  function onPointerUp(event) {
    if (!draft) return;
    const completed = { ...draft };
    delete completed.startX;
    delete completed.startY;
    state.addCamera(completed);
    draft = null;
    elements.overlay.releasePointerCapture(event.pointerId);
    setTool("select");
    render();
    scheduleSave();
  }

  async function initialize() {
    try {
      const [payload] = await Promise.all([
        loadProject(documentUrl, controller.signal),
        elements.image.decode(),
      ]);
      dimensions = {
        width: elements.image.naturalWidth,
        height: elements.image.naturalHeight,
      };
      elements.overlay.setAttribute("viewBox", `0 0 ${dimensions.width} ${dimensions.height}`);
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
    draft = null;
    render();
  });
  elements.notes.addEventListener("input", () => {
    updateControls();
    scheduleSave();
  });
  elements.undo.addEventListener("click", () => {
    if (state.undo()) {
      render();
      scheduleSave();
    }
  });
  elements.deleteSelection.addEventListener("click", () => {
    if (state.deleteSelected()) {
      render();
      scheduleSave();
    }
  });
  window.addEventListener("pagehide", () => controller.abort(), { once: true });

  initialize();
}
