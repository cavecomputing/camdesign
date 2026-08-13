function clone(value) {
  return structuredClone(value);
}

export function createEditorState(initialDocument) {
  let current = clone(initialDocument);
  const history = [];
  let selectedId = null;

  function checkpoint() {
    history.push(clone(current));
    if (history.length > 50) history.shift();
  }

  return {
    document() {
      return clone(current);
    },
    itemsWith(draft) {
      return draft ? [...current.items, draft] : current.items;
    },
    cameraCount() {
      return current.items.filter((item) => item.type === "camera").length;
    },
    itemById(itemId) {
      const item = current.items.find((entry) => entry.id === itemId);
      return item ? clone(item) : null;
    },
    addCamera(camera) {
      checkpoint();
      current.items.push(clone(camera));
      selectedId = camera.id;
    },
    beginChange() {
      checkpoint();
    },
    updateItem(itemId, changes) {
      const item = current.items.find((entry) => entry.id === itemId);
      if (!item) return false;
      Object.assign(item, changes);
      return true;
    },
    deleteSelected() {
      if (!selectedId) return false;
      const nextItems = current.items.filter((item) => item.id !== selectedId);
      if (nextItems.length === current.items.length) return false;
      checkpoint();
      current.items = nextItems;
      selectedId = null;
      return true;
    },
    undo() {
      const previous = history.pop();
      if (!previous) return false;
      current = previous;
      selectedId = null;
      return true;
    },
    canUndo() {
      return history.length > 0;
    },
    selectedId() {
      return selectedId;
    },
    select(itemId) {
      selectedId = current.items.some((item) => item.id === itemId) ? itemId : null;
    },
  };
}
