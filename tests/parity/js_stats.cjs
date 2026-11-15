// Statistics of the team's simulator (field_shift/front/analysis.js, as embedded in docs/visualizacao.html),
// printed as JSON so tests/parity/compare.py can test the Python engine against it.
//   node tests/parity/js_stats.cjs <trajectories> <seed>
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");

const [count = "20000", seed = "2026"] = process.argv.slice(2);
const page = fs.readFileSync(path.join(__dirname, "../../docs/visualizacao.html"), "utf8");
const script = [...page.matchAll(/<script>\s*(.*?)<\/script>/gs)][0][1];
const core = script.slice(0, script.indexOf("for(const item of cases.cases)"));

// Same DOM stub as tests/test_front.cjs: every element exists; only the JSON payloads have text.
const payloads = new Map([...page.matchAll(/<script id="([^"]+)" type="application\/json">(.*?)<\/script>/gs)].map(m => [m[1], m[2]]));
const context = { console, document: { getElementById: id => ({ textContent: payloads.get(id) }) } };
vm.createContext(context);
vm.runInContext(core + `
function caseStats(profileId, start, count, seed) {
  active = profiles[profileId];
  const history = Object.entries(active.water_markov.environment_years)
    .filter(([, block]) => Array.isArray(block) && block.length === active.water_markov.periods_per_year);
  const inputs = active.economics.crop_inputs;
  const selected = new Set(Object.keys(inputs).filter(id => Boolean(inputs[id].include_in_vpl ?? inputs[id].eligible_for_economic_comparison)));
  const rng = seeded(seed), finalCrop = {}, routes = {}, values = [];
  for (let i = 0; i < count; i++) {
    const result = sampleTrajectory(start, rng, history, initialSugarcaneCut(start));
    finalCrop[result.crop] = (finalCrop[result.crop] || 0) + 1;
    const key = actualRouteEvents(result.path).crops.join(",");
    routes[key] = (routes[key] || 0) + 1;
    const scored = scoreTrajectoryVpl(result.path, inputs, selected);
    if (scored) values.push(scored.vpl);
  }
  values.sort((a, b) => a - b);
  const mean = values.reduce((sum, v) => sum + v, 0) / Math.max(1, values.length);
  const sd = Math.sqrt(values.reduce((sum, v) => sum + (v - mean) ** 2, 0) / Math.max(1, values.length - 1));
  return { profile: profileId, start, count, final_crop: finalCrop, routes, priced: values.length,
           value: { mean, sd, p5: quantileSorted(values, 0.05), p50: quantileSorted(values, 0.5), p95: quantileSorted(values, 0.95) } };
}
`, context);
const initialSugarcaneCut = start => 1;
context.initialSugarcaneCut = initialSugarcaneCut;
const cases = [];
for (const profile of ["ariquemes-ro", "franca-sp", "varginha-mg"])
  for (const start of ["soybean", "maize_grain", "sugarcane"])
    cases.push(vm.runInContext(`caseStats(${JSON.stringify(profile)}, ${JSON.stringify(start)}, ${Number(count)}, ${Number(seed)})`, context));
process.stdout.write(JSON.stringify(cases));
