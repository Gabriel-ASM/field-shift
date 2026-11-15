const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");
const root = path.join(__dirname, "..");
const page = fs.readFileSync(path.join(root, "docs/visualizacao.html"), "utf8");
const payloads = new Map([...page.matchAll(/<script id="([^"]+)" type="application\/json">(.*?)<\/script>/gs)].map(m => [m[1], m[2]]));
const scripts = [...page.matchAll(/<script>\s*(.*?)<\/script>/gs)];
const analysis = scripts[0][1];
// Run the actual embedded simulation without attaching UI listeners.
const core = analysis.slice(0, analysis.indexOf("for(const item of cases.cases)"));
assert.ok(core.length > 0 && scripts.length === 2);
vm.runInNewContext(core + `
  active = profiles["ariquemes-ro"];
  const history = Object.entries(active.water_markov.environment_years);
  const maize = "maize_grain";
  let match;
  for (let seed = 1; seed <= 1000; seed++) {
    const result = sampleTrajectory("soybean", seeded(seed), history);
    const harvests = result.path.filter(step => step.eventKind === "main_harvest");
    if (harvests.slice(0, 4).map(step => step.crop).join(",") === "soybean,maize_grain,maize_grain,maize_grain") {
      match = {seed, result, harvests};
      break;
    }
  }
  assert.ok(match, "expected a seeded path with three consecutive maize harvests");
  const {seed, result, harvests} = match;
  const maizeHarvests = harvests.slice(1, 4);
  assert.equal(maizeHarvests.map(s => s.consecutivePlantings).join(","), "1,2,3");
  assert.equal(maizeHarvests.map(s => s.repeatYieldMultiplier).join(","), "1,0.978,0.957");
  assert.equal(repeatedCropYieldMultiplier(maize, 10), 0.957);
  assert.equal(repeatedCropYieldMultiplier("sugarcane", 3), 1);
  assert.equal(waterClass(active.water_classes.low_max_inclusive), "water_low");
  assert.equal(waterClass(active.water_classes.medium_max_inclusive), "water_medium");
  assert.equal(waterClass(1), "water_high");
  for (const frame of result.environmentPath) {
    assert.ok(frame.waterFraction >= 0 && frame.waterFraction <= 1);
    assert.equal(frame.water, waterClass(frame.waterFraction));
  }
  const inputs = active.economics.crop_inputs, selected = new Set(Object.keys(inputs));
  const neutral = result.path.map(step => maizeHarvests.includes(step) ? {...step, repeatYieldMultiplier: 1} : step);
  const delta = maizeHarvests.reduce((sum, step) => {
    const input = inputs[maize], years = step.day / cropCycles.time_basis.days_per_year;
    const gross = input.yield_kg_ha_median_2021_2025 / 1000 * priceAtYear(input, years) * economicYieldMultiplier(step.water, step.soc);
    const cost = input.cost_panel.total_cost_brl_ha_reference_month;
    assert.ok(Math.abs(economicCashflow(step, inputs) - (gross * step.repeatYieldMultiplier - cost)) < 1e-8);
    return sum + gross * (1 - step.repeatYieldMultiplier) / (1 + active.economics.discount_rate.real_annual_rate_approx) ** years;
  }, 0);
  const discountedLoss = scoreTrajectoryVpl(neutral, inputs, selected).vpl - scoreTrajectoryVpl(result.path, inputs, selected).vpl;
  assert.ok(delta > 0 && Math.abs(discountedLoss - delta) < 1e-8);
  console.log("Seed " + seed + ": soybean -> maize -> maize -> maize; confirmed discounted loss R$/ha " + delta.toFixed(2));
`, {
  assert, console,
  document: {getElementById: id => ({textContent: payloads.get(id)})},
});
