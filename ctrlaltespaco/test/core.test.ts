import assert from "node:assert/strict";
import { test } from "node:test";
import { tilePlacement, tilesCovering, tileUrl, toWorld } from "../src/geo/mercator.ts";
import { sharesAt } from "../src/scene/occupancy.ts";
import { chainCrops, scenariosFor, suggestedRotation } from "../src/scenarios.ts";

test("mercator puts the equator and Greenwich in the middle of the world", () => {
  assert.deepEqual(toWorld([0, 0]), [16, 16]);
  assert.ok(toWorld([-47, -20])[1] > 16, "south of the equator is further down");
});

test("tiles cover a box and know where they lie", () => {
  assert.equal(tilesCovering([-84, 14], [-28, -42], 5).length, 6 * 7);
  assert.deepEqual(tilePlacement({ x: 80, y: 136, zoom: 8 }), { size: 0.125, centre: [10.0625, 17.0625] });
  assert.equal(tileUrl("t/{z}/{y}/{x}.jpeg", { x: 1, y: 2, zoom: 3 }), "t/3/2/1.jpeg");
});

test("occupancy is interpolated between years", () => {
  const occupancy: Record<string, number>[] = [{ soybean: 1 }, { soybean: 0.5, maize_grain: 0.5 }];
  assert.deepEqual(sharesAt(occupancy, ["soybean", "maize_grain"], 0.5), [0.75, 0.25]);
  assert.deepEqual(sharesAt(occupancy, ["soybean", "maize_grain"], 9), [0.5, 0.5]);
});

test("the suggested rotation is the starting crop and its likeliest other successor", () => {
  const matrix = {
    initial_state: "soybean:skip_stages",
    states: ["soybean:skip_stages", "maize_grain:skip_stages", "fallow:skip_stages"],
    rows: [{ from: "soybean:skip_stages", cells: [{ probability: 0.6 }, { probability: 0.4 }, null] }],
  };
  assert.deepEqual(suggestedRotation(matrix), ["soybean", "maize_grain"]);
  assert.deepEqual(chainCrops(matrix), ["soybean", "maize_grain"]);
  assert.equal(scenariosFor(["soybean"])[1]!.policy.kind, "rotation");
});
