import assert from "node:assert/strict";
import { test } from "node:test";
import { cropShapes } from "../src/ui/cropArt.ts";

test("soybean, maize and sugarcane have their own drawing; other crops share the plant in their leaf colour", () => {
  const drawn = ["soybean", "maize_grain", "sugarcane"].map((crop) => cropShapes(crop).map(({ d }) => d).join());
  assert.equal(new Set(drawn).size, 3);
  const [millet, wheat] = [cropShapes("millet"), cropShapes("wheat")];
  assert.deepEqual(millet.map(({ d }) => d), wheat.map(({ d }) => d));
  assert.notEqual(millet[2]!.fill, wheat[2]!.fill);
  assert.equal(cropShapes("fallow").length, 1, "fallow is bare ground");
  assert.ok(cropShapes("unknown_crop").length > 1);
});

test("cane gets darker at each cut, starting from its own colour", async () => {
  const { caneShade } = await import("../src/ui/caneShade.ts");
  const { cropColor } = await import("../src/ui/colors.ts");
  assert.equal(caneShade(1, 5), cropColor("sugarcane"));
  const brightness = (hex: string) => [1, 3, 5].reduce((sum, at) => sum + parseInt(hex.slice(at, at + 2), 16), 0);
  const shades = [1, 2, 3, 4, 5].map((cut) => brightness(caneShade(cut, 5)));
  assert.ok(shades.every((value, index) => index === 0 || value < shades[index - 1]!));
});
