// A single-select dropdown that can be typed into to narrow the list, with a second
// grey line of detail under each option. Neither <select> nor <datalist> can carry that
// subtext, so this is the ARIA combobox pattern built by hand.
//
// Options look like { value, label, meta, group }. `value` is what gets stored, `label`
// is the bold first line, `meta` the grey second line, `group` an optional heading the
// option is filed under.

let sequence = 0;

function optionMatches(option, query) {
  const haystack = `${option.label} ${option.meta ?? ""}`.toLowerCase();
  return query.every((word) => haystack.includes(word));
}

// Everything the editor calls on a combobox, doing nothing. Picking equipment is an aid
// to filling in a quote; drawing the plan is the job. If a control's markup is missing —
// a cached template served against fresh JS will do it — the editor has to keep placing
// and aiming cameras rather than die on the way to its own event listeners.
function inertCombobox(label) {
  console.warn(`CamDesign: the ${label} dropdown is missing its markup and is inactive.`);
  return { setOptions() {}, setValue() {}, setPlaceholder() {}, setDisabled() {} };
}

export function createCombobox(root, { onCommit, emptyLabel = "None", name = "equipment" }) {
  const input = root?.querySelector(".combo__input");
  const list = root?.querySelector(".combo__list");
  if (!input || !list) return inertCombobox(name);
  const id = `combo-${(sequence += 1)}`;

  list.id = `${id}-list`;
  input.setAttribute("aria-controls", list.id);

  let options = [];
  let visible = [];
  let activeIndex = -1;
  let value = "";
  // Null until the first keystroke: opening the list shows everything rather than
  // filtering by the label already sitting in the box.
  let query = null;

  function labelFor(candidate) {
    return options.find((option) => option.value === candidate)?.label ?? candidate;
  }

  function isOpen() {
    return !list.hidden;
  }

  function renderList() {
    const words = query ? query.toLowerCase().split(/\s+/).filter(Boolean) : [];
    visible = words.length
      ? options.filter((option) => optionMatches(option, words))
      : options.slice();

    const rows = [];
    let group = null;
    for (const option of visible) {
      if (option.group && option.group !== group) {
        group = option.group;
        const heading = document.createElement("li");
        heading.className = "combo__group";
        heading.setAttribute("role", "presentation");
        heading.textContent = group;
        rows.push(heading);
      }
      const row = document.createElement("li");
      row.className = "combo__option";
      row.id = `${id}-option-${rows.length}`;
      row.setAttribute("role", "option");
      row.setAttribute("aria-selected", String(option.value === value));
      row.dataset.value = option.value;

      const name = document.createElement("span");
      name.className = "combo__option-name";
      name.textContent = option.label;
      row.append(name);
      if (option.meta) {
        const meta = document.createElement("span");
        meta.className = "combo__option-meta";
        meta.textContent = option.meta;
        row.append(meta);
      }
      rows.push(row);
    }

    if (!visible.length) {
      const empty = document.createElement("li");
      empty.className = "combo__empty";
      empty.setAttribute("role", "presentation");
      empty.textContent = "No match";
      rows.push(empty);
    }
    list.replaceChildren(...rows);
    setActive(visible.findIndex((option) => option.value === value));
  }

  function rowFor(index) {
    return index < 0 ? null : list.querySelector(`[data-value="${CSS.escape(visible[index].value)}"]`);
  }

  function setActive(index) {
    activeIndex = index >= 0 && index < visible.length ? index : -1;
    for (const row of list.querySelectorAll(".combo__option")) {
      row.classList.remove("is-active");
    }
    const row = rowFor(activeIndex);
    if (!row) {
      input.removeAttribute("aria-activedescendant");
      return;
    }
    row.classList.add("is-active");
    input.setAttribute("aria-activedescendant", row.id);
    row.scrollIntoView({ block: "nearest" });
  }

  function open() {
    if (isOpen() || input.disabled) return;
    query = null;
    renderList();
    list.hidden = false;
    root.classList.add("is-open");
    input.setAttribute("aria-expanded", "true");
  }

  function close() {
    if (!isOpen()) return;
    list.hidden = true;
    root.classList.remove("is-open");
    input.setAttribute("aria-expanded", "false");
    input.removeAttribute("aria-activedescendant");
    query = null;
    activeIndex = -1;
    // Whatever half-typed search is in the box is not the value; show the value again.
    input.value = labelFor(value);
  }

  function commit(next) {
    const changed = next !== value;
    value = next;
    close();
    input.value = labelFor(value);
    if (changed) onCommit(value);
  }

  function move(step) {
    if (!isOpen()) {
      open();
      if (activeIndex >= 0) return;
    }
    if (!visible.length) return;
    const from = activeIndex < 0 ? (step > 0 ? -1 : 0) : activeIndex;
    setActive((from + step + visible.length) % visible.length);
  }

  // The box shows the committed label, so typing has to replace it rather than run on
  // the end of it. Focus highlights the label; the guard keeps the click that caused
  // the focus from immediately collapsing that selection to a caret.
  let selectOnFocus = false;
  input.addEventListener("focus", () => {
    selectOnFocus = true;
    open();
    input.select();
  });
  input.addEventListener("pointerdown", open);
  input.addEventListener("mouseup", (event) => {
    if (!selectOnFocus) return;
    selectOnFocus = false;
    event.preventDefault();
  });
  input.addEventListener("input", () => {
    query = input.value;
    if (!isOpen()) {
      list.hidden = false;
      root.classList.add("is-open");
      input.setAttribute("aria-expanded", "true");
    }
    renderList();
    // Typing aims at the top of what is left rather than at the current value, which
    // has usually just been filtered out of sight.
    setActive(visible.length ? 0 : -1);
  });
  input.addEventListener("keydown", (event) => {
    if (event.key === "ArrowDown") {
      event.preventDefault();
      move(1);
      return;
    }
    if (event.key === "ArrowUp") {
      event.preventDefault();
      move(-1);
      return;
    }
    if (event.key === "Enter") {
      if (!isOpen()) return;
      event.preventDefault();
      commit(activeIndex >= 0 ? visible[activeIndex].value : value);
      return;
    }
    if (event.key === "Escape" && isOpen()) {
      // Only the list closes. Escape with the list already shut belongs to the editor,
      // which uses it to drop the camera selection.
      event.stopPropagation();
      close();
      return;
    }
    if (event.key === "Tab") close();
  });
  input.addEventListener("blur", () => {
    selectOnFocus = false;
    // Emptying the box and leaving it is how the field gets cleared.
    if (isOpen() && input.value.trim() === "" && value !== "") {
      commit("");
      return;
    }
    close();
  });
  // Down on an option would blur the input and close the list before the click landed.
  list.addEventListener("pointerdown", (event) => event.preventDefault());
  list.addEventListener("click", (event) => {
    const row = event.target.closest(".combo__option");
    if (row) commit(row.dataset.value);
  });

  return {
    setOptions(next) {
      options = [{ value: "", label: emptyLabel, meta: "" }, ...next];
      if (isOpen()) renderList();
      input.value = labelFor(value);
    },
    setValue(next) {
      value = next ?? "";
      close();
      input.value = labelFor(value);
    },
    setPlaceholder(text) {
      input.placeholder = text;
    },
    setDisabled(disabled) {
      input.disabled = disabled;
      root.classList.toggle("is-disabled", disabled);
      if (disabled) close();
    },
  };
}
