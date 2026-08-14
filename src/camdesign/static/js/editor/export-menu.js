// The Export button, which is a menu button: one format today, more as the quote
// package grows. Built by hand for the same reason the equipment dropdowns are — the
// second grey line under each format is what tells them apart.

// Chrome and Firefox both revoke a still-attached object URL out from under the
// download if it goes too soon, so hold it for a beat rather than in the next tick.
const REVOKE_AFTER_MS = 20_000;

export function downloadBlob(blob, filename) {
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = filename;
  link.hidden = true;
  document.body.append(link);
  link.click();
  link.remove();
  window.setTimeout(() => URL.revokeObjectURL(url), REVOKE_AFTER_MS);
}

export function createExportMenu(root, { onSelect }) {
  const toggle = root?.querySelector("[data-export-toggle]");
  const list = root?.querySelector("[data-export-list]");
  // Losing the menu costs the estimator an export, not the plan they are drawing, so
  // a missing control stays quiet and leaves the rest of the editor alone.
  if (!toggle || !list) return;

  const items = [...list.querySelectorAll("[data-export-url]")];

  function isOpen() {
    return !list.hidden;
  }

  function setOpen(open) {
    list.hidden = !open;
    root.classList.toggle("is-open", open);
    toggle.setAttribute("aria-expanded", String(open));
  }

  function close({ restoreFocus = false } = {}) {
    if (!isOpen()) return;
    setOpen(false);
    if (restoreFocus) toggle.focus();
  }

  function open(focusIndex = -1) {
    setOpen(true);
    if (focusIndex >= 0) items.at(focusIndex)?.focus();
  }

  function step(delta) {
    const index = items.indexOf(document.activeElement);
    const next = index < 0 ? 0 : (index + delta + items.length) % items.length;
    items[next]?.focus();
  }

  toggle.addEventListener("click", () => (isOpen() ? close() : open()));

  for (const item of items) {
    item.addEventListener("click", () => {
      // Closed before the work starts: the export takes a moment, and a menu left
      // hanging open over the plan reads as a click that did not land.
      close({ restoreFocus: true });
      onSelect(item.dataset.exportUrl);
    });
  }

  // Scoped to the menu, which is where focus is whenever it is open. Escape has to stop
  // here rather than reach the editor's own ladder, which would drop the plan's
  // selection on the way to closing a menu sitting on top of it.
  root.addEventListener("keydown", (event) => {
    if (event.key === "Escape" && isOpen()) {
      event.stopPropagation();
      close({ restoreFocus: true });
      return;
    }
    if (event.key !== "ArrowDown" && event.key !== "ArrowUp") return;
    event.preventDefault();
    if (!isOpen()) {
      open(event.key === "ArrowDown" ? 0 : -1);
      return;
    }
    step(event.key === "ArrowDown" ? 1 : -1);
  });

  document.addEventListener("pointerdown", (event) => {
    if (!root.contains(event.target)) close();
  });
  root.addEventListener("focusout", (event) => {
    if (!root.contains(event.relatedTarget)) close();
  });
}
