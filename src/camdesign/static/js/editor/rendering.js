const SVG_NS = "http://www.w3.org/2000/svg";

function svgElement(name, attributes = {}) {
  const element = document.createElementNS(SVG_NS, name);
  for (const [key, value] of Object.entries(attributes)) {
    element.setAttribute(key, String(value));
  }
  return element;
}

function cameraGroup(camera, dimensions, index, selected) {
  const { width, height } = dimensions;
  const scale = Math.max(1, Math.min(width, height) / 800);
  const x = camera.x * width;
  const y = camera.y * height;
  const radius = camera.range * Math.min(width, height);
  const direction = (camera.direction_degrees * Math.PI) / 180;
  const halfAngle = (camera.fov_degrees * Math.PI) / 360;
  const startAngle = direction - halfAngle;
  const endAngle = direction + halfAngle;
  const startX = x + Math.cos(startAngle) * radius;
  const startY = y + Math.sin(startAngle) * radius;
  const endX = x + Math.cos(endAngle) * radius;
  const endY = y + Math.sin(endAngle) * radius;
  const largeArc = camera.fov_degrees > 180 ? 1 : 0;

  const group = svgElement("g", {
    class: `camera-item${selected ? " is-selected" : ""}`,
    "data-item-id": camera.id,
    tabindex: "0",
    role: "button",
    "aria-label": camera.label || `Camera ${index + 1}`,
  });
  group.append(
    svgElement("path", {
      class: "camera-cone",
      d: `M ${x} ${y} L ${startX} ${startY} A ${radius} ${radius} 0 ${largeArc} 1 ${endX} ${endY} Z`,
    }),
    // Invisible grab target so the move handle stays usable on a touch screen.
    svgElement("circle", {
      class: "camera-handle",
      "data-camera-handle": "",
      cx: x,
      cy: y,
      r: 20 * scale,
    }),
    svgElement("circle", {
      class: "camera-source",
      "data-camera-handle": "",
      cx: x,
      cy: y,
      r: 9 * scale,
    }),
    // Geometry is set by layoutLabels once the text has been measured. The chip sits
    // under the glyphs and carries the hit target for clicking a name.
    svgElement("rect", { class: "camera-label", "data-camera-name": "", rx: 5 * scale }),
  );
  const label = svgElement("text", {
    class: "camera-label-text",
    "text-anchor": "start",
    "font-size": 13 * scale,
  });
  label.textContent = camera.label || `C${String(index + 1).padStart(2, "0")}`;
  group.append(label);
  group.dataset.scale = String(scale);
  group.dataset.originX = String(x);
  group.dataset.originY = String(y);
  return group;
}

function overlaps(a, b) {
  return !(
    a.x + a.width <= b.x ||
    b.x + b.width <= a.x ||
    a.y + a.height <= b.y ||
    b.y + b.height <= a.y
  );
}

// Where a name may sit relative to its camera, best first: beside it, then flipped,
// then above or below, then stepped further away.
function labelCandidates(x, y, w, h, scale) {
  const gap = 14 * scale;
  const baseline = y + 4.5 * scale;
  const step = h + 12 * scale;
  const candidates = [
    { tx: x + gap, ty: baseline },
    { tx: x - gap - w, ty: baseline },
    { tx: x - w / 2, ty: y - gap },
    { tx: x - w / 2, ty: y + gap + h },
  ];
  for (let n = 1; n <= 8; n += 1) {
    candidates.push({ tx: x + gap, ty: baseline - n * step });
    candidates.push({ tx: x + gap, ty: baseline + n * step });
    candidates.push({ tx: x - gap - w, ty: baseline - n * step });
    candidates.push({ tx: x - gap - w, ty: baseline + n * step });
  }
  return candidates;
}

// Names are free text and cameras cluster, so chips are sized from the rendered
// glyphs and nudged off one another instead of sitting at a fixed offset.
function layoutLabels(overlay, dimensions) {
  const groups = [...overlay.children];

  // Park every label at a reference point first, so all the measuring below happens
  // in one layout pass rather than thrashing between reads and writes.
  for (const group of groups) {
    const text = group.querySelector(".camera-label-text");
    text.setAttribute("x", group.dataset.originX);
    text.setAttribute("y", group.dataset.originY);
  }
  const measured = groups.map((group) => {
    const box = group.querySelector(".camera-label-text").getBBox();
    return {
      group,
      width: box.width,
      height: box.height,
      offsetX: box.x - Number(group.dataset.originX),
      offsetY: box.y - Number(group.dataset.originY),
    };
  });

  const placed = [];
  for (const { group, width, height, offsetX, offsetY } of measured) {
    const scale = Number(group.dataset.scale);
    const x = Number(group.dataset.originX);
    const y = Number(group.dataset.originY);
    const padX = 7 * scale;
    const padY = 5 * scale;

    const rectFor = (candidate) => ({
      x: candidate.tx + offsetX - padX,
      y: candidate.ty + offsetY - padY,
      width: width + padX * 2,
      height: height + padY * 2,
    });
    const onPlan = (rect) =>
      rect.x >= 0 &&
      rect.y >= 0 &&
      rect.x + rect.width <= dimensions.width &&
      rect.y + rect.height <= dimensions.height;

    const candidates = labelCandidates(x, y, width, height, scale);
    const chosen =
      candidates.find((candidate) => {
        const rect = rectFor(candidate);
        return onPlan(rect) && !placed.some((other) => overlaps(rect, other));
      }) ??
      candidates.find(
        (candidate) => !placed.some((other) => overlaps(rectFor(candidate), other)),
      ) ??
      candidates[0];

    const rect = rectFor(chosen);
    const text = group.querySelector(".camera-label-text");
    const chip = group.querySelector(".camera-label");
    text.setAttribute("x", chosen.tx);
    text.setAttribute("y", chosen.ty);
    chip.setAttribute("x", rect.x);
    chip.setAttribute("y", rect.y);
    chip.setAttribute("width", rect.width);
    chip.setAttribute("height", rect.height);
    placed.push(rect);
  }
}

export function renderPlan(overlay, items, dimensions, selectedId) {
  overlay.replaceChildren(
    ...items.map((item, index) =>
      cameraGroup(item, dimensions, index, item.id === selectedId),
    ),
  );
  layoutLabels(overlay, dimensions);
}
