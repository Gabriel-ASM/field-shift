import assert from "node:assert/strict";
import { test } from "node:test";
import { rank, recommended, scoreOnTen, supportScore, weights } from "../src/ranking.ts";
import { regionScenario } from "../src/scenarios.ts";
import type { RankingSettings, Route } from "../src/types.ts";

const SETTINGS: RankingSettings = {
  minimum: 0, maximum: 10, break_even: 5, minimum_scale: 1, minimum_samples: 100,
  support: { weight: 0.15, minimum_ranked: 2, minimum_recommended: 20, full_score: 100 },
  environment_weight: { default_weight: 0.2, maximum_weight: 0.5, weight_step: 0.05 },
  soil_share: 2 / 3, water_share: 1 / 3, soil_reference: 20, water_scale: 0.2,
};

function route(crops: string[], median: number, carbon: number, samples = 500): Route {
  const value = { mean: median, p5: median - 1000, p50: median, p95: median + 1000, cvar5: median - 2000, count: samples };
  return { crops, share: 0.1, value, final_carbon: carbon, final_water_multiplier: 1 };
}

test("the journey simulates the region from the farmer's crop", () => {
  assert.deepEqual(regionScenario("maize_grain"), {
    id: "region", label: "What the region usually does", initial_state: "maize_grain:skip_stages", policy: { kind: "markov" },
  });
});

test("score is break-even at zero and saturates at the scale", () => {
  assert.equal(scoreOnTen(0, 100, SETTINGS), 5);
  assert.equal(scoreOnTen(100, 100, SETTINGS), 10);
  assert.equal(scoreOnTen(-500, 100, SETTINGS), 0);
});

test("priorities change which sequence wins", () => {
  const rich = route(["soybean", "maize_grain"], 9000, 8);
  const careful = route(["soybean", "brachiaria"], 7000, 26);
  assert.equal(rank([rich, careful], SETTINGS, 0)[0]!.route, rich);
  assert.equal(rank([rich, careful], SETTINGS, 0.5)[0]!.route, careful);
});

test("support has a fixed share and grows with the priced scenarios up to the full score", () => {
  assert.deepEqual(weights(0.2, SETTINGS), { support: 0.15, environment: 0.85 * 0.2, economic: 1 - 0.15 - 0.85 * 0.2 });
  assert.equal(supportScore(50, SETTINGS), 5);
  assert.equal(supportScore(100, SETTINGS), 10);
  assert.equal(supportScore(1000, SETTINGS), 10);
});

test("thin sequences are ranked as exploratory but never recommended; single or unpriced ones are left out", () => {
  const solid = route(["soybean"], 1000, 20);
  const thin = route(["maize_grain"], 99999, 20, 3);
  const single = route(["sorghum_grain"], 99999, 20, 1);
  const unpriced: Route = { ...route(["millet"], 0, 20), value: null };
  const ranked = rank([solid, thin, single, unpriced], SETTINGS, 0.2);
  assert.deepEqual(ranked.map(({ route: item }) => item), [thin, solid]);
  assert.equal(recommended(ranked, SETTINGS)!.route, solid);
  assert.equal(recommended(rank([thin], SETTINGS, 0.2), SETTINGS), undefined);
});
