// Reproducible sensitivity audit using the generated simulator, without the UI.
const fs = require('node:fs'), path = require('node:path');
const page = fs.readFileSync(path.join(__dirname, '../docs/visualizacao.html'), 'utf8');
const payloads = new Map([...page.matchAll(/<script id="([^"]+)" type="application\/json">(.*?)<\/script>/gs)].map(m => [m[1],m[2]]));
const script = [...page.matchAll(/<script>\s*(.*?)<\/script>/gs)][0][1];
new Function('document', 'console', 'currentPolicy', 'sampleCount', script.slice(0,script.indexOf('for(const item of cases.cases)')) + `
active=profiles['ariquemes-ro'];
// Reproduce the historical penalty-cap comparison independently of the later
// maize/soybean exclusion policy, which is covered by test_front.cjs.
if(!currentPolicy)cropCycles.sequence_constraints.break_required_between_crop_groups=[];
const selected=new Set(Object.entries(active.economics.crop_inputs).filter(([,v])=>v.include_in_vpl??v.eligible_for_economic_comparison).map(([k])=>k));
for(const guard of currentPolicy?[true]:[false,true]){
  cropCycles.repeated_crop_effect.block_replant_after_penalty_cap=guard;
  const rng=seeded(2026), groups=new Map(), history=Object.entries(active.water_markov.environment_years);
  let violations=0;
  const cropOccurrences={};
  for(let i=0;i<sampleCount;i++){
    const result=sampleTrajectory('maize_grain',rng,history);
    for(const crop of new Set(result.path.filter(e=>e.eventKind==='planting'||e.eventKind==='start').map(e=>e.crop)))cropOccurrences[crop]=(cropOccurrences[crop]||0)+1;
    for(const event of result.path)if(event.eventKind==='planting'&&event.crop===event.fromCrop&&replantBlockedAtPenaltyCap(event.crop,event.consecutivePlantings-1))violations++;
    addRotationSample(groups,result,active.economics.crop_inputs,selected);
  }
  const rows=[...groups].filter(([key,s])=>s.values.length>=minimumRankedVplSamples&&JSON.parse(key).crops.every(c=>c==='fallow'||selected.has(c))).map(([key,s])=>{
    const v=[...s.values].sort((a,b)=>a-b),tail=v.slice(0,Math.ceil(v.length*.05));
    return {key,s,n:v.length,count:v.length,median:quantileSorted(v,.5),p95:quantileSorted(v,.95),cvar:tail.reduce((a,b)=>a+b,0)/tail.length};
  });
  const all=rows.flatMap(r=>r.s.values).sort((a,b)=>a-b),tail=all.slice(0,Math.ceil(all.length*.05));
  const scale=Math.max(Math.abs(tail.reduce((a,b)=>a+b,0)/tail.length),Math.abs(quantileSorted(all,.95)),1);
  for(const r of rows){
    const env=Number(rankingEnvironmentSettings.soil_share)*soilScoreOnTen(r.s.finalSocSum/r.s.finalEnvironmentCount)+Number(rankingEnvironmentSettings.water_share)*waterScoreOnTen(waterMultiplierMean(r.s.finalWaterCounts));
    const economic=scoreOnTen((r.p95+r.cvar)/2,scale);
    r.priorityScore10=.8*economic+.2*env;
    r.score=rotationScore(economic,env,rotationSupportScore(r.n),rotationScoreWeights(.2));
  }
  rows.sort((a,b)=>b.score-a.score||b.median-a.median||a.key.localeCompare(b.key));
  const best=rows.find(r=>r.n>=minimumRecommendedVplSamples);
  const byLength={};
  for(const r of rows){const length=JSON.parse(r.key).crops.length,bin=byLength[length]??={routes:0,recommendable:0,fullSupport:0};bin.routes++;bin.recommendable+=Number(r.n>=minimumRecommendedVplSamples);bin.fullSupport+=Number(r.n>=rankingSupportSettings.full_score_vpl_samples);}
  const describe=r=>r&&({sequence:JSON.parse(r.key),count:r.n,median:r.median,cvar:r.cvar,p95:r.p95,score:r.score,priorityScore:r.priorityScore10});
  console.log(JSON.stringify({currentPolicy,guard,seed:2026,trajectories:sampleCount,cropOccurrences,violations,byLength,best:describe(best),bestWithoutSupport:describe(bestRouteWithoutSupport(rows))}));
  if(violations)throw Error('Replant guard violated');
}
`)({getElementById:id=>({textContent:payloads.get(id)})}, console, process.argv.includes('--current'), Number(process.argv.find(arg=>arg.startsWith('--samples='))?.split('=')[1]||100000));
