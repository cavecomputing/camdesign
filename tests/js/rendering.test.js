import assert from "node:assert/strict";
import test from "node:test";

import { cameraWarnings } from "../../src/camdesign/static/js/editor/rendering.js";

const catalog = [
  {
    make: "Hanwha",
    models: [{ model: "XND-A9084RV" }],
    licenses: [{ sku: "WAVE-PRO-01" }],
  },
  {
    make: "Generic",
    models: [{ model: "Generic camera" }],
    licenses: [],
  },
];

test("a camera reports each incomplete equipment choice", () => {
  assert.deepEqual(cameraWarnings({ make: "Hanwha", model: "", license: "" }, catalog), [
    "model not specified",
    "license not specified",
  ]);
  assert.deepEqual(
    cameraWarnings({ make: "Hanwha", model: "XND-A9084RV", license: "" }, catalog),
    ["license not specified"],
  );
});

test("a fully configured or generic camera has no warning", () => {
  assert.deepEqual(
    cameraWarnings(
      { make: "Hanwha", model: "XND-A9084RV", license: "WAVE-PRO-01" },
      catalog,
    ),
    [],
  );
  assert.deepEqual(
    cameraWarnings({ make: "Generic", model: "Generic camera", license: "" }, catalog),
    [],
  );
});
