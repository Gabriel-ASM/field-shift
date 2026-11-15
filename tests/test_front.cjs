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
assert.deepEqual([...page.matchAll(/class="crop-choice"[^>]*data-crop="([^"]+)"/g)].map(match => match[1]),
  ["soybean", "maize_grain", "sugarcane"]);
vm.runInNewContext(core + `
  active = profiles["ariquemes-ro"];
  const history = Object.entries(active.water_markov.environment_years);
  const maize = "maize_grain";
  const exclusiveGroups = cropCycles.sequence_constraints.break_required_between_crop_groups;
  const choices = new Set([maize, "soybean", "sugarcane"]);
  assert.deepEqual([...sequenceEligibleDestinations(maize, choices)], [maize, "sugarcane"]);
  assert.deepEqual([...sequenceEligibleDestinations("soybean", choices)], ["soybean", "sugarcane"]);
  assert.deepEqual([...sequenceEligibleDestinations("sorghum_grain", choices)], [...choices]);
  assert.deepEqual([...sequenceEligibleDestinations("brachiaria", choices)], [...choices]);
  assert.equal(choices.size, 3, "must not mutate cached candidates");
  assert.equal(sequenceEligibleDestinations(maize, new Set(["soybean"])).size, 0);
  let observedReturnAfterBreak=false;
  for(const profile of Object.values(profiles)){
    active=profile;
    const sorgo=active.economics.crop_inputs.sorghum_grain,milheto=active.economics.crop_inputs.millet;
    assert.ok(sorgo.include_in_vpl&&sorgo.price.history_start_year>=2017&&!sorgo.cost_panel.cover_management);
    assert.ok(milheto.include_in_vpl&&milheto.cost_panel.cover_management);
    assert.equal(milheto.price.brl_per_tonne,0);
    const years=Object.entries(active.water_markov.environment_years);
    for(const start of [maize, "soybean", "sugarcane"]){
      for(let seed=1;seed<=30;seed++){
        const trajectory=sampleTrajectory(start,seeded(seed),years);
        const planted=trajectory.path.filter(event=>event.eventKind==="start"||event.eventKind==="planting").map(event=>event.crop);
        if(planted.includes(maize)&&planted.includes("soybean"))observedReturnAfterBreak=true;
        for(let i=1;i<planted.length;i++)assert.ok(!(planted[i]!==planted[i-1]&&[maize,"soybean"].includes(planted[i])&&[maize,"soybean"].includes(planted[i-1])), "maize and soybean need an intervening crop");
      }
    }
  }
  active=profiles["ariquemes-ro"];
  assert.ok(observedReturnAfterBreak, "a completed intermediate crop must allow maize and soybean in the same trajectory");
  // Legacy cashflow regression deliberately disables the new eligibility policy.
  cropCycles.sequence_constraints.break_required_between_crop_groups=[];
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
  assert.equal(replantBlockedAtPenaltyCap(maize, 2), false);
  assert.equal(replantBlockedAtPenaltyCap(maize, 3), true);
  assert.equal(replantBlockedAtPenaltyCap("soybean", 3), false);
  assert.equal(replantBlockedAtPenaltyCap("soybean", 4), true);
  assert.equal(replantBlockedAtPenaltyCap("sugarcane", 10), false);
  const cachedDestinations = new Set([maize, "soybean"]);
  assert.deepEqual([...constrainedReplantDestinations(maize, 3, cachedDestinations)], ["soybean"]);
  assert.equal(cachedDestinations.has(maize), true);
  assert.equal(constrainedReplantDestinations(maize, 3, new Set([maize])).size, 0);
  assert.equal(waterClass(active.water_classes.low_max_inclusive), "water_low");
  assert.equal(waterClass(active.water_classes.medium_max_inclusive), "water_medium");
  assert.equal(waterClass(1), "water_high");
  for (const frame of result.environmentPath) {
    assert.ok(frame.waterFraction >= 0 && frame.waterFraction <= 1);
    assert.equal(frame.water, waterClass(frame.waterFraction));
  }
  const inputs = active.economics.crop_inputs, selected = new Set(Object.keys(inputs));
  const coverStart={eventKind:"planting",crop:"brachiaria",day:100};
  const coverEnd={eventKind:"main_harvest",flowKind:"main_harvest",flowCrop:"brachiaria",crop:"brachiaria",day:190};
  const soyStart={eventKind:"planting",crop:"soybean",day:220};
  const soyEnd={eventKind:"main_harvest",flowKind:"main_harvest",flowCrop:"soybean",crop:"soybean",day:340,water:"water_medium",soc:12};
  const discount=day=>(1+active.economics.discount_rate.real_annual_rate_approx)**(day/365);
  const coverCost=inputs.brachiaria.cost_panel.total_cost_brl_ha_reference_month;
  assert.ok(Math.abs(economicCashflow(coverStart,inputs)+economicCashflow(coverEnd,inputs)+coverCost)<1e-8);
  assert.equal(scoreTrajectoryVpl([{crop:maize},coverStart],inputs,selected).vpl,economicCashflow(coverStart,inputs)/discount(100));
  const nextSoy={...soyStart,day:380},nextHarvest={...soyEnd,day:500};
  const pathWithCover=[{crop:maize},coverStart,coverEnd,soyStart,soyEnd,nextSoy,nextHarvest];
  const withoutResidual={...inputs,brachiaria:{...inputs.brachiaria,cost_panel:{...inputs.brachiaria.cost_panel,cover_management:{...inputs.brachiaria.cost_panel.cover_management,soybean_residual:null}}}};
  const addedVpl=scoreTrajectoryVpl(pathWithCover,inputs,selected).vpl-scoreTrajectoryVpl(pathWithCover,withoutResidual,selected).vpl;
  const soyGross=economicCashflow(soyEnd,inputs)+inputs.soybean.cost_panel.total_cost_brl_ha_reference_month;
  assert.ok(Math.abs(addedVpl-soyGross*.045/discount(340))<1e-8,"residual only on first soybean and with decay");
  assert.equal(coverResidualGain(coverEnd,{...soyStart,day:310},inputs),0);
  assert.equal(coverResidualGain(coverEnd,{...soyStart,crop:maize},inputs),0);
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
  cropCycles.sequence_constraints.break_required_between_crop_groups=exclusiveGroups;

  active = profiles["varginha-mg"];
  const cane = "sugarcane";
  const caneHistory = Object.entries(active.water_markov.environment_years);
  const cuts = sampleTrajectory(cane, seeded(2026), caneHistory).path.filter(step => step.eventKind === "main_harvest");
  assert.equal(cuts.length, 5);
  assert.ok(Math.abs(cuts.at(-1).day - 1825) < 1e-8);
  assert.equal(cuts.map(step => step.sugarcane_cut).join(","), "1,2,3,4,5");

  const lateCane = sampleTrajectory(cane, seeded(2026), caneHistory, 4).path;
  const caneHarvests = lateCane.filter(step => step.flowKind === "main_harvest" && step.crop === cane);
  assert.equal(caneHarvests.map(step => step.sugarcane_cut).join(","), "4,5");
  assert.equal(lateCane.find(step => step.eventKind === "sugarcane_reform").day, 730);
  const afterReform = lateCane.find(step => step.eventKind === "planting");
  assert.ok(sugarcaneReformDestinations().has(afterReform.crop));
  assert.ok(plantingDecendiosForCrop(afterReform.crop).includes(afterReform.plantingDecendio));
  assert.ok(afterReform.day >= 730);
  assert.equal(lateCane.some(step => step.flowKind === "perennial_formation_cost"), false);

  for (const profile of Object.values(profiles)) {
    assert.equal(profile.crop_markov.initial_crop_ids.join(","), "soybean,maize_grain,sugarcane");
    assert.equal(profile.crop_markov.states.find(state => state.id === cane).initial_selectable, true);
    assert.ok(profile.crop_markov.transitions.some(edge => edge.from === "soybean" && edge.to === cane));
  }
  const economicCrops = new Set(active.economics.economically_supported_crop_ids);
  const groups = new Map(), expected = new Map(), climateRng = seeded(2026);
  for (let i = 0; i < 300; i++) {
    const trajectory = sampleTrajectory(cane, climateRng, caneHistory, 2);
    const key = JSON.stringify(actualRouteEvents(trajectory.path));
    addRotationSample(groups, trajectory, active.economics.crop_inputs, economicCrops);
    if (!expected.has(key)) expected.set(key, []);
    expected.get(key).push(trajectory);
  }
  const [sampleKey, sample] = [...groups].sort((a, b) => b[1].frequency - a[1].frequency)[0];
  const matching = expected.get(sampleKey), frames = rotationEnvironmentFrames(sample);
  assert.ok(groups.size > 1 && matching.length < 300);
  assert.equal(frames.length, 121);
  for (let year = 0; year <= 5; year++) {
    const frame = frames[year * 24];
    for (const [water, count] of Object.entries(frame.water)) {
      assert.equal(count, matching.filter(trajectory => trajectory.environmentPath[year].water === water).length);
    }
    const soilClassById = {soil_degraded:"low", soil_regular:"medium", soil_good:"high"};
    for (const [soil, count] of Object.entries(frame.soil)) {
      assert.equal(count, matching.filter(trajectory => soilCarbonClass(trajectory.environmentPath[year].soc) === soilClassById[soil]).length);
    }
  }
  addRotationSample(groups, matching[0], active.economics.crop_inputs, economicCrops);
  assert.equal(Object.values(rotationEnvironmentFrames(sample).at(-1).water).reduce((a,b)=>a+b), matching.length+1);

  const financial = rotationScoreWeights(0), mixed = rotationScoreWeights(.2);
  assert.equal(financial.economic, .85);
  assert.equal(financial.support, .15);
  assert.ok(Math.abs(mixed.environment - .17) < 1e-9 && Math.abs(mixed.economic - .68) < 1e-9);
  assert.equal(rotationSupportScore(50), 5);
  assert.equal(rotationSupportScore(100), 10);
  assert.equal(rotationSupportScore(1000), 10);
  assert.ok(rotationScore(8, 0, rotationSupportScore(1), financial) <
    rotationScore(7, 0, rotationSupportScore(100), financial),
    "a well-supported sequence can overtake a higher raw economic score");

  let viableCaneRoute = false;
  for (let seed = 1; seed <= 1000 && !viableCaneRoute; seed++) {
    const {path} = sampleTrajectory("soybean", seeded(seed), caneHistory);
    const planting = path.find(step => step.eventKind === "planting" && step.crop === cane);
    const harvest = path.find(step => step.flowKind === "main_harvest" && step.crop === cane);
    if (planting && harvest && scoreTrajectoryVpl(path, active.economics.crop_inputs, economicCrops)) {
      assert.ok(harvest.day - planting.day >= cycleRule(cane).maturation_days);
      assert.equal(harvest.sugarcane_cut, 1);
      viableCaneRoute = true;
    }
  }
  assert.ok(viableCaneRoute, "the ordinary rotation should include a scoreable cane route");
  console.log("Confirmed standing cane starts at the selected cut, reforms after cut 5, and newly planted cane starts at cut 1.");
`, {
  assert, console,
  document: {getElementById: id => ({textContent: payloads.get(id)})},
});
