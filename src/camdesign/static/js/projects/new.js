const field = document.querySelector("[data-upload-field]");

if (field) {
  const input = field.querySelector('input[type="file"]');
  const icon = field.querySelector("[data-upload-icon]");
  const title = field.querySelector("[data-upload-title]");
  const detail = field.querySelector("[data-upload-detail]");
  const initial = {
    icon: icon.textContent,
    title: title.textContent,
    detail: detail.textContent,
  };
  // Mirrors the server's allow-list; drops bypass the input's accept filter.
  const ACCEPTED_TYPES = new Set(["image/png", "image/jpeg", "image/webp"]);
  let dragDepth = 0;

  function formatSize(bytes) {
    if (bytes >= 1_000_000) return `${(bytes / 1_000_000).toFixed(1)} MB`;
    if (bytes >= 1_000) return `${Math.round(bytes / 1_000)} KB`;
    return `${bytes} B`;
  }

  function showFile(file) {
    field.classList.remove("has-error");
    field.classList.add("has-file");
    icon.textContent = "✓";
    title.textContent = file.name;
    detail.textContent = `${formatSize(file.size)} · click or drop another image to replace it`;
  }

  function showError(message) {
    // Whatever state the field shows must be what actually submits.
    input.value = "";
    field.classList.remove("has-file");
    field.classList.add("has-error");
    icon.textContent = "!";
    title.textContent = message;
    detail.textContent = "Use a PNG, JPEG, or WebP image.";
  }

  function reset() {
    field.classList.remove("has-file", "has-error");
    icon.textContent = initial.icon;
    title.textContent = initial.title;
    detail.textContent = initial.detail;
  }

  input.addEventListener("change", () => {
    const file = input.files?.[0];
    if (file) showFile(file);
    else reset();
  });

  field.addEventListener("dragenter", (event) => {
    event.preventDefault();
    dragDepth += 1;
    field.classList.add("is-dragover");
  });
  // dragover has to be cancelled every time or the drop itself is rejected.
  field.addEventListener("dragover", (event) => {
    event.preventDefault();
  });
  field.addEventListener("dragleave", () => {
    // Entering a child fires leave for the parent, so only clear at the edge.
    dragDepth = Math.max(0, dragDepth - 1);
    if (dragDepth === 0) field.classList.remove("is-dragover");
  });
  field.addEventListener("drop", (event) => {
    event.preventDefault();
    dragDepth = 0;
    field.classList.remove("is-dragover");
    const file = event.dataTransfer?.files?.[0];
    if (!file) return;
    if (!ACCEPTED_TYPES.has(file.type)) {
      showError("That file type won't work");
      return;
    }
    try {
      input.files = event.dataTransfer.files;
      showFile(file);
    } catch {
      showError("Couldn't read that file — try the picker instead");
    }
  });
}
