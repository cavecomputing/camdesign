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
    shortcuts: [...root.querySelectorAll("[data-shortcut]")],
    cameraTitle: root.querySelector("[data-camera-title]"),
    cameraEmpty: root.querySelector("[data-camera-empty]"),
    cameraFields: root.querySelector("[data-camera-fields]"),
    cameraLabel: root.querySelector("[data-camera-label]"),
    cameraNote: root.querySelector("[data-camera-note]"),
    cameraNoteCount: root.querySelector("[data-camera-note-count]"),
  };

  const FIRST_RETRY_MS = 1_000;
  const MAX_RETRY_MS = 15_000;
  const ADJUST_THRESHOLD_PX = 4;
  const MIN_ZOOM = 1;
  const MAX_ZOOM = 8;
  const MIN_FOV = 30;
  const MAX_FOV = 180;
  const DEFAULT_FOV = 90;

  const documentUrl = root.dataset.documentUrl;
  let state;
  let revision;
  let dimensions;
  let activeTool = "select";
  let draft = null;
  let adjust = null;
  let move = null;
  let pan = null;
  let cameraFieldDirty = false;
  let zoom = 1;
  let baseWidth = 0;
  let offsetX = 0;
  let offsetY = 0;
  let originX = 0;
  let originY = 0;
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
      setSaveState("Catching up…", "saving");
      scheduleRetry(200);
      return;
    }
    // Restarting the server mints a new secret key, which quietly invalidates the
    // session holding the CSRF token. Fetch a fresh one rather than lose the work.
    if (error.status === 400 && !csrfRefreshed && (await refreshCsrfToken())) {
      csrfRefreshed = true;
      setSaveState("Reconnecting…", "saving");
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
        setSaveState("Saving…", "saving");
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
          savedVersion === changeVersion ? "saved" : "dirty",
        );
      })
      .catch((error) => {
        if (error.name !== "AbortError") return handleSaveFailure(error);
      });
    return saveQueue;
  }

  function markChanged() {
    changeVersion += 1;
    setSaveState("Unsaved changes", "dirty");
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
    // Retoggle the class so the swap animation replays on every tool change.
    elements.hint.classList.remove("is-swap");
    void elements.hint.offsetWidth;
    elements.hint.classList.add("is-swap");
    elements.overlay.style.cursor = tool === "camera" ? "crosshair" : "grab";
  }

  function pointFromEvent(event) {
    const bounds = elements.overlay.getBoundingClientRect();
    return {
      x: ((event.clientX - bounds.left) / bounds.width) * dimensions.width,
      y: ((event.clientY - bounds.top) / bounds.height) * dimensions.height,
    };
  }

  // The fit width and the corner the stage is pinned to both come from the stylesheet, so
  // read them back with the zoom sizing and the offset stripped off. Re-measured whenever
  // the panel changes shape: stale figures size and place the plan against a layout that
  // no longer exists, and it jumps on the next zoom step.
  function measureFit() {
    const zoomed = elements.stage.classList.contains("is-zoomed");
    const sized = elements.stage.style.width;
    const placed = elements.stage.style.transform;
    elements.stage.classList.remove("is-zoomed");
    elements.stage.style.width = "";
    elements.stage.style.transform = "";
    const resting = elements.stage.getBoundingClientRect();
    baseWidth = elements.image.getBoundingClientRect().width;
    originX = resting.left;
    originY = resting.top;
    elements.stage.style.width = sized;
    elements.stage.style.transform = placed;
    elements.stage.classList.toggle("is-zoomed", zoomed);
  }

  // Sizing the stage rather than scaling it keeps the browser resampling the plan at the
  // size it is shown, which is the difference between reading a door number at 8x and not.
  function sizeStage() {
    elements.stage.classList.toggle("is-zoomed", zoom !== MIN_ZOOM);
    elements.stage.style.width = zoom === MIN_ZOOM ? "" : `${baseWidth * zoom}px`;
  }

  // The only thing worth enforcing while zoomed is that the plan cannot be lost: half of
  // it, or half the panel once it is the bigger of the two, has to stay in view. Demanding
  // that it cover the panel outright would be tidier, but it fights the cursor — a plan
  // sitting in the middle with a gap above it has to lurch upwards the moment a zoom step
  // makes it taller than the panel, which is exactly the jump this is meant to avoid.
  function clampOffset(offset, start, size, min, max) {
    const keep = Math.min(size, max - min) / 2;
    return Math.min(max - keep - start, Math.max(min + keep - size - start, offset));
  }

  function applyView() {
    // All the way out is the one view with a right answer: the whole plan, centred.
    if (zoom === MIN_ZOOM) centreView();
    const panel = elements.panel.getBoundingClientRect();
    const stage = elements.stage.getBoundingClientRect();
    offsetX = Math.round(clampOffset(offsetX, originX, stage.width, panel.left, panel.right));
    offsetY = Math.round(clampOffset(offsetY, originY, stage.height, panel.top, panel.bottom));
    elements.stage.style.transform = `translate(${offsetX}px, ${offsetY}px)`;
  }

  function centreView() {
    const panel = elements.panel.getBoundingClientRect();
    const stage = elements.stage.getBoundingClientRect();
    offsetX = panel.left + (panel.width - stage.width) / 2 - originX;
    offsetY = panel.top + (panel.height - stage.height) / 2 - originY;
  }

  function applyZoom(nextZoom, anchor) {
    const clamped = Math.min(MAX_ZOOM, Math.max(MIN_ZOOM, nextZoom));
    if (!baseWidth || clamped === zoom) return;
    // Note where on the plan the cursor is before resizing, as a fraction of the stage.
    const before = elements.stage.getBoundingClientRect();
    const ratioX = before.width ? (anchor.x - before.left) / before.width : 0.5;
    const ratioY = before.height ? (anchor.y - before.top) / before.height : 0.5;

    zoom = clamped;
    sizeStage();

    // Then slide the stage so that same spot is back under the cursor.
    const after = elements.stage.getBoundingClientRect();
    offsetX += anchor.x - (after.left + ratioX * after.width);
    offsetY += anchor.y - (after.top + ratioY * after.height);
    applyView();
  }

  function fitPlan() {
    zoom = MIN_ZOOM;
    sizeStage();
    applyView();
  }

  function onWheel(event) {
    if (!dimensions) return;
    event.preventDefault();
    // Normalise line and page scrolling to pixels so every input device steps evenly.
    const lines = event.deltaMode === 1 ? 16 : event.deltaMode === 2 ? 400 : 1;
    const factor = Math.exp((-event.deltaY * lines) / 650);
    applyZoom(zoom * factor, { x: event.clientX, y: event.clientY });
  }

  function currentFov() {
    const value = Number(elements.fov.value);
    if (!Number.isFinite(value) || elements.fov.value.trim() === "") return DEFAULT_FOV;
    return Math.min(MAX_FOV, Math.max(MIN_FOV, Math.round(value)));
  }

  function updateCameraNoteCount() {
    elements.cameraNoteCount.textContent = `${elements.cameraNote.value.length} / 1000`;
  }

  // Point the inspector at whatever is selected, so the fields always edit what is
  // highlighted on the plan. Kept out of render() so a redraw cannot clobber typing.
  function syncSelectionPanel() {
    const selected = state?.selectedId();
    const camera = selected ? state.itemById(selected) : null;
    elements.cameraFields.hidden = !camera;
    elements.cameraEmpty.hidden = Boolean(camera);
    elements.cameraNoteCount.hidden = !camera;
    elements.cameraTitle.textContent = camera
      ? camera.label || "Unnamed camera"
      : "None selected";
    if (camera) elements.fov.value = String(Math.round(camera.fov_degrees));
    elements.cameraLabel.value = camera ? camera.label : "";
    elements.cameraNote.value = camera ? camera.note : "";
    updateCameraNoteCount();
    cameraFieldDirty = false;
  }

  function applyCameraField(changes) {
    const selected = state?.selectedId();
    if (!selected) return;
    // One checkpoint per editing session rather than per keystroke, so undo steps
    // back the whole edit the way the drag gestures do.
    if (!cameraFieldDirty) {
      state.beginChange();
      cameraFieldDirty = true;
    }
    state.updateItem(selected, changes);
    render();
    markChanged();
  }

  function deleteSelectedCamera() {
    if (!state?.deleteSelected()) return;
    syncSelectionPanel();
    render();
    markChanged();
  }

  function undoLastChange() {
    if (!state?.undo()) return;
    syncSelectionPanel();
    render();
    markChanged();
  }

  function rangeFromDistance(distance) {
    return Math.min(2, Math.max(0.03, distance / Math.min(dimensions.width, dimensions.height)));
  }

  // Counting items reuses a number after a delete, producing two C03s. Carry on from
  // the highest auto name instead, and ignore cameras the user has renamed.
  function nextCameraLabel() {
    const used = state
      .document()
      .items.map((item) => /^C(\d+)$/.exec(item.label ?? ""))
      .filter(Boolean)
      .map((match) => Number(match[1]));
    const next = used.length ? Math.max(...used) + 1 : 1;
    return `C${String(next).padStart(2, "0")}`;
  }

  function cameraFromPoint(point) {
    return {
      id: crypto.randomUUID(),
      type: "camera",
      x: point.x / dimensions.width,
      y: point.y / dimensions.height,
      direction_degrees: -90,
      fov_degrees: currentFov(),
      range: 0.16,
      label: nextCameraLabel(),
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
      offsetX,
      offsetY,
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
      syncSelectionPanel();
      const camera = itemId ? state.itemById(itemId) : null;
      if (camera && event.target.closest?.("[data-camera-name]")) {
        // A name can sit well away from its camera once labels have been nudged
        // apart, so clicking it selects and nothing more. Dragging the name must
        // not re-aim the camera at the name.
        render();
        return;
      }
      if (camera && event.target.closest?.("[data-camera-handle]")) {
        // The circle at the cone's point is the body: drag it to reposition the camera.
        move = {
          id: itemId,
          originX: camera.x,
          originY: camera.y,
          start: pointFromEvent(event),
          clientX: event.clientX,
          clientY: event.clientY,
          started: false,
        };
        capturePointer(event.pointerId);
      } else if (camera) {
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
    // The armed tool wins: a camera can be dropped on top of an existing one.
    if (activeTool !== "camera") return;
    event.preventDefault();
    const point = pointFromEvent(event);
    draft = cameraFromPoint(point);
    draft.startX = point.x;
    draft.startY = point.y;
    capturePointer(event.pointerId);
    render();
  }

  function onPointerMove(event) {
    if (pan) {
      offsetX = pan.offsetX + (event.clientX - pan.clientX);
      offsetY = pan.offsetY + (event.clientY - pan.clientY);
      applyView();
      return;
    }
    if (move) {
      const travelled = Math.hypot(event.clientX - move.clientX, event.clientY - move.clientY);
      if (!move.started && travelled < ADJUST_THRESHOLD_PX) return;
      if (!move.started) {
        state.beginChange();
        move.started = true;
      }
      const point = pointFromEvent(event);
      const x = move.originX + (point.x - move.start.x) / dimensions.width;
      const y = move.originY + (point.y - move.start.y) / dimensions.height;
      // Cameras are stored as a fraction of the image, so keep them on the plan.
      state.updateItem(move.id, {
        x: Math.min(1, Math.max(0, x)),
        y: Math.min(1, Math.max(0, y)),
      });
      render();
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
    if (move || adjust) {
      const changed = Boolean(move?.started || adjust?.started);
      move = null;
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
    // The tool stays armed so a run of cameras can be placed without reselecting it.
    syncSelectionPanel();
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
      measureFit();
      // Nothing else places the stage: it is pinned to a corner until the view centres it.
      fitPlan();
      state = createEditorState(payload.document);
      revision = payload.revision;
      elements.notes.value = payload.project.notes;
      setSaveState("All changes saved", "saved");
      syncSelectionPanel();
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
    const edited = Boolean(adjust?.started || move?.started);
    draft = null;
    adjust = null;
    move = null;
    pan = null;
    render();
    // The camera was already changed before the gesture was cancelled, so persist it.
    if (edited) markChanged();
  });
  document.addEventListener("keydown", (event) => {
    const typing = Boolean(
      event.target.closest?.("input, textarea, select, [contenteditable]"),
    );

    if ((event.ctrlKey || event.metaKey) && !event.altKey && event.key.toLowerCase() === "z") {
      // Inside a text field this belongs to the browser's own text undo.
      if (typing) return;
      event.preventDefault();
      undoLastChange();
      return;
    }
    if (event.ctrlKey || event.metaKey || event.altKey) return;

    // Escape backs out one step at a time, so holding it down walks all the way to a
    // plain Select tool with nothing highlighted: leave the field, drop the selection,
    // then put the armed tool away.
    if (event.key === "Escape") {
      if (typing) {
        event.target.blur?.();
        return;
      }
      if (state?.selectedId()) {
        state.select(null);
        syncSelectionPanel();
        render();
        return;
      }
      if (activeTool !== "select") setTool("select");
      return;
    }

    // Everything below would fight with typing a name, a note, or an angle.
    if (typing) return;

    if (event.key === "Delete" || event.key === "Backspace") {
      if (!state?.selectedId()) return;
      event.preventDefault();
      deleteSelectedCamera();
      return;
    }

    const button = elements.shortcuts.find((entry) => entry.dataset.shortcut === event.key);
    if (!button || button.disabled || !button.dataset.tool) return;
    event.preventDefault();
    setTool(button.dataset.tool);
  });

  elements.cameraLabel.addEventListener("focus", () => {
    cameraFieldDirty = false;
  });
  elements.cameraLabel.addEventListener("input", () => {
    applyCameraField({ label: elements.cameraLabel.value });
    elements.cameraTitle.textContent = elements.cameraLabel.value || "Unnamed camera";
  });
  elements.cameraLabel.addEventListener("blur", () => {
    // Every camera needs an identifier on the quote, so a cleared name falls back
    // to the next unused auto name rather than leaving a blank chip on the plan.
    if (!state?.selectedId() || elements.cameraLabel.value.trim() !== "") return;
    const label = nextCameraLabel();
    elements.cameraLabel.value = label;
    elements.cameraTitle.textContent = label;
    applyCameraField({ label });
  });
  elements.cameraNote.addEventListener("focus", () => {
    cameraFieldDirty = false;
  });
  elements.cameraNote.addEventListener("input", () => {
    updateCameraNoteCount();
    applyCameraField({ note: elements.cameraNote.value });
  });

  elements.fov.addEventListener("change", () => {
    const fov = currentFov();
    // Reflect the clamped value so the number shown is the number that gets used.
    elements.fov.value = String(fov);
    // While the camera tool is armed this is the angle for the next camera, so leave
    // the one just placed alone. Retargeting a camera is a Select-tool action.
    const selected = activeTool === "select" ? state?.selectedId() : null;
    if (!selected) return;
    state.beginChange();
    state.updateItem(selected, { fov_degrees: fov });
    render();
    markChanged();
  });

  elements.panel.addEventListener("wheel", onWheel, { passive: false });
  // Suppress the Windows middle-click autoscroll ring so the pan gesture owns the button.
  elements.overlay.addEventListener("auxclick", (event) => {
    if (event.button === 1) event.preventDefault();
  });
  elements.overlay.addEventListener("dblclick", (event) => {
    if (activeTool !== "select" || event.target.closest?.("[data-item-id]")) return;
    fitPlan();
  });
  // The fit width follows the panel, which moves for reasons a window resize misses:
  // a wrapping toolbar, a scrollbar in the inspector, the tablet turning on its side.
  let refitting = false;
  new ResizeObserver(() => {
    if (!dimensions || refitting) return;
    refitting = true;
    // Wait for the frame to settle before measuring. Read straight from the callback and
    // the plan is still being sized against the window the browser is halfway out of.
    requestAnimationFrame(() => {
      refitting = false;
      measureFit();
      sizeStage();
      // Zoomed in this holds the spot being worked on; at fit it re-centres the plan in
      // whatever shape the panel has just become.
      applyView();
    });
  }).observe(elements.panel);
  elements.notes.addEventListener("input", () => {
    updateControls();
    markChanged();
  });
  elements.undo.addEventListener("click", undoLastChange);
  elements.deleteSelection.addEventListener("click", deleteSelectedCamera);
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
