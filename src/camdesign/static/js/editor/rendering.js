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
    svgElement("rect", {
      class: "camera-label",
      x: x + 12 * scale,
      y: y - 11 * scale,
      width: 42 * scale,
      height: 22 * scale,
      rx: 5 * scale,
    }),
  );
  const label = svgElement("text", {
    class: "camera-label-text",
    x: x + 33 * scale,
    y: y + 4 * scale,
    "text-anchor": "middle",
    "font-size": 13 * scale,
  });
  label.textContent = camera.label || `C${String(index + 1).padStart(2, "0")}`;
  group.append(label);
  return group;
}

export function renderPlan(overlay, items, dimensions, selectedId) {
  overlay.replaceChildren(
    ...items.map((item, index) =>
      cameraGroup(item, dimensions, index, item.id === selectedId),
    ),
  );
}
