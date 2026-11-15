import assert from "node:assert/strict";
import { test } from "node:test";
import { preference, rank, recommended, scoreOnTen, supportScore, weights } from "../src/ranking.ts";
import { bandwidth, density } from "../src/ui/density.ts";
import { regionScenario } from "../src/scenarios.ts";
import { groupTracks, segments } from "../src/ui/tracks.ts";
import type { RankingReference, RankingSettings, Route } from "../src/types.ts";

const SETTINGS: RankingSettings = {
  minimum: 0, maximum: 10, break_even: 5, minimum_scale: 1, minimum_samples: 100, return_weight: { default: 0.5, step: 0.05 },
  support: { weight: 0.15, minimum_ranked: 2, minimum_recommended: 20, full_score: 100 },
  environment_weight: { default_weight: 0.2, maximum_weight: 0.5, weight_step: 0.05 },
  soil_share: 2 / 3, water_share: 1 / 3, soil_reference: 20, water_scale: 0.2,
  carbon_share_within_soil: 0.67, nitrogen_share_within_soil: 0.33, nitrogen_target_per_carbon: 300, nitrogen_ratio_limits: [0.8, 1.2],
};

function route(crops: string[], median: number, carbon: number, samples = 500): Route {
  const value = { mean: median, p5: median - 1000, p50: median, p95: median + 1000, cvar5: median - 2000, count: samples, loss_probability: 0.1 };
  return { crops, share: 0.1, trajectories: samples, value, final_carbon: carbon, final_carbon_class: "medium", final_water_multiplier: 1,
    final_water: { water_low: 0.2, water_medium: 0.5, water_high: 0.3 }, final_water_fraction: 0.5, final_total_nitrogen: carbon * 300, yield_penalty: crops.map(() => 0) };
}

const REFERENCE: RankingReference = { cvar5: -1000, p95: 10000, count: 1000, routes: 3 };
const balance = (weight: number, returnWeight = 0.5) => ({ weight, returnWeight });

test("the journey simulates the region from the farmer's crop", () => {
  assert.deepEqual(regionScenario("maize_grain"), {
    id: "region", label: "What the region usually does", initial_state: "maize_grain:skip_stages", policy: { kind: "markov" },
  });
});

test("standing cane sends the next cut; other crops do not send the field", () => {
  assert.equal(regionScenario("sugarcane", 4).initial_sugarcane_cut, 4);
  assert.equal(regionScenario("sugarcane").initial_sugarcane_cut, 2, "the default is the 2nd cut: the 1st is not offered");
  assert.equal("initial_sugarcane_cut" in regionScenario("soybean", 4), false);
});

test("score is break-even at zero and saturates at the scale", () => {
  assert.equal(scoreOnTen(0, 100, SETTINGS), 5);
  assert.equal(scoreOnTen(100, 100, SETTINGS), 10);
  assert.equal(scoreOnTen(-500, 100, SETTINGS), 0);
});

test("priorities change which sequence wins", () => {
  const rich = route(["soybean", "maize_grain"], 9000, 8);
  const careful = route(["soybean", "brachiaria"], 7000, 26);
  assert.equal(rank([rich, careful], REFERENCE, SETTINGS, balance(0))[0]!.route, rich);
  assert.equal(rank([rich, careful], REFERENCE, SETTINGS, balance(0.5))[0]!.route, careful);
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
  const ranked = rank([solid, thin, single, unpriced], REFERENCE, SETTINGS, balance(0.2));
  assert.deepEqual(ranked.map(({ route: item }) => item), [thin, solid]);
  assert.equal(recommended(ranked, SETTINGS)!.route, solid);
  assert.equal(recommended(rank([thin], REFERENCE, SETTINGS, balance(0.2)), SETTINGS), undefined);
});

test("alpha moves the economic score between the worst outcomes and the high return", () => {
  const steady = route(["soybean"], 5000, 20);
  assert.equal(preference(steady, 0), steady.value!.cvar5);
  assert.equal(preference(steady, 1), steady.value!.p95);
  const risky = { ...route(["maize_grain"], 5000, 20), value: { ...steady.value!, cvar5: -9000, p95: 12000 } };
  assert.equal(rank([steady, risky], REFERENCE, SETTINGS, balance(0.2, 0))[0]!.route, steady);
  assert.equal(rank([steady, risky], REFERENCE, SETTINGS, balance(0.2, 1))[0]!.route, risky);
});

test("the return curve smooths the histogram with the producer.js bandwidth and peaks near the mode", () => {
  const distribution = { start: 0, width: 10, counts: [0, 2, 10, 2, 0], sd: 7, q25: 20, q75: 30 };
  assert.equal(bandwidth(distribution), Math.max(1, 50 / 200, 0.9 * Math.min(7, 10 / 1.34) * 14 ** -0.2));
  const curve = density(distribution);
  const peak = curve.points.reduce((best, point) => (point.density > best.density ? point : best));
  assert.ok(Math.abs(peak.value - 25) < 2 && curve.points.length === 151);
});

test("the result view starts on the first recommendable sequence and can switch to another option", async () => {
  const { options, routeKey, selectRoute } = await import("../src/ranking.ts");
  const first = route(["soybean", "maize_grain"], 9000, 20), second = route(["soybean", "brachiaria"], 8000, 20);
  const thin = route(["maize_grain"], 99999, 20, 3);
  const ranked = rank([second, thin, first], REFERENCE, SETTINGS, balance(0.2));
  assert.equal(selectRoute(ranked, SETTINGS, null)!.route, recommended(ranked, SETTINGS)!.route);
  assert.equal(selectRoute(ranked, SETTINGS, routeKey(second))!.route, second);
  assert.equal(selectRoute(ranked, SETTINGS, routeKey(thin))!.route, recommended(ranked, SETTINGS)!.route, "exploratory ones are not options");
  assert.deepEqual(options(ranked, SETTINGS, 5).map(({ route: item }) => item).includes(thin), false);
});

test("total N scores against the C:N target of the route's final carbon", async () => {
  const { nitrogenClass, nitrogenScore } = await import("../src/ranking.ts");
  const at = (ratio: number) => ({ ...route(["soybean"], 1000, 20), final_total_nitrogen: 20 * 300 * ratio });
  assert.equal(nitrogenScore(at(0.5), SETTINGS), 5);
  assert.equal(nitrogenScore(at(2), SETTINGS), 10);
  assert.deepEqual([0.5, 1, 1.3].map((ratio) => nitrogenClass(at(ratio), SETTINGS)), ["low", "medium", "high"]);
});


test("identical trajectories form one group and consecutive periods merge into stretches", () => {
  const same = { crop: ["soybean", "soybean", "fallow", "sugarcane", "sugarcane"], cane_cut: [0, 0, 0, 1, 2] };
  const other = { crop: ["soybean", "fallow", "fallow", "sugarcane", "sugarcane"], cane_cut: [0, 0, 0, 1, 1] };
  const groups = groupTracks([same, { ...same }, other]);
  assert.deepEqual(groups.map((group) => group.count), [2, 1]);
  assert.deepEqual(segments(same).map(({ crop, cut, start, end }) => [crop, cut, start, end]), [
    ["soybean", 0, 0, 2], ["fallow", 0, 2, 3], ["sugarcane", 1, 3, 4], ["sugarcane", 2, 4, 5]]);
});

import { decendioOfDay, plantings, windowText } from "../src/result/plan.ts";

test("plantings read off a trajectory and ZARC windows in words", () => {
  assert.equal(decendioOfDay(0), 1);
  assert.equal(decendioOfDay(273), 28);      // October 1st
  const track = { crop: ["soybean", "fallow", "maize_grain", "maize_grain", "sugarcane", "sugarcane"], cane_cut: [0, 0, 0, 0, 1, 2] };
  assert.deepEqual(plantings(track, 4), [{ crop: "maize_grain", year: 1, decendio: 19 }, { crop: "sugarcane", year: 2, decendio: 1 }]);
  assert.equal(windowText({ 1: 20, 27: 30, 28: 30, 29: 20, 30: 20, 36: 20 }), "late Sep – early Oct (30%), mid Oct – late Oct (20%), late Dec – early Jan (20%)");
});

import { centre, distanceKm, nearest } from "../src/map/places.ts";

test("the nearest complete profile to a searched municipality", () => {
  const ring: [number, number][] = [[-48, -21], [-47, -21], [-47, -20], [-48, -20], [-48, -21]];
  const square = { features: [{ geometry: { type: "Polygon" as const, coordinates: [ring] } }] };
  assert.deepEqual(centre(square), [-20.5, -47.5]);
  assert.ok(Math.abs(distanceKm([0, 0], [0, 1]) - 111.2) < 0.1);
  const at = (id: string, lat: number, long: number) => ({ id, initial_node: { climate: { lat, long } } }) as never;
  const found = nearest([at("far", -9.9, -63), at("close", -20.5, -47.4)], [-20.5, -47.5])!;
  assert.equal((found.profile as unknown as { id: string }).id, "close");
  assert.ok(found.km < 20);
});
