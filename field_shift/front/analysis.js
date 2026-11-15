
const cases=JSON.parse(document.getElementById("cases").textContent);
const profiles=JSON.parse(document.getElementById("profiles").textContent);
const soilHypotheses=JSON.parse(document.getElementById("soil-hypotheses").textContent);
const cropCycles=JSON.parse(document.getElementById("crop-cycles").textContent);
const formationFractionBaseline={...cropCycles.new_perennial_formation};
const economicData=JSON.parse(document.getElementById("economic-data").textContent);
const runSettings=JSON.parse(document.getElementById("run-settings").textContent);
const monteCarloSettings=runSettings.monte_carlo;
const rankingScoreSettings=runSettings.ranking_score;
const rankingEnvironmentSettings=rankingScoreSettings.environment;
const waterLabels={water_low:"Baixa",water_medium:"Média",water_high:"Alta"};
const rainLabels={dry:"seca",normal:"normal",wet:"úmida"};
const maxTrajectories=Number(monteCarloSettings.maximum_trajectories),horizon=5,horizonMonths=Number(cropCycles.time_basis.horizon_months),horizonDays=horizonMonths*Number(cropCycles.time_basis.days_per_year)/12,climatePeriodDays=Number(cropCycles.time_basis.days_per_year)/Number(cropCycles.time_basis.environment_periods_per_year),rankingPageSize=25;
let active=null,latestRun=null,simulationSession=null,selectedGraphCropId=null,cachedCropStateProfile=null,cachedCropStatesById=null,cachedCropTransitionProfile=null,cachedCropTransitions=null,cachedCalendarProfile=null,cachedCropPlantingWindows=null,cachedPlantingDecendios=null,cachedCropCalendarBasis=null,cachedAllowedProfile=null,cachedAllowedBySource=null,cachedEligibleBySource=null,cachedScheduleProfile=null,cachedPlantingSchedules=null,cachedWaterProfile=null,cachedWaterRows=null,simulationRunId=0,rotationRankingPage=0;
const graphIntervalCache=new Map();

function byId(id){return document.getElementById(id);}
const environmentWeightControl=byId("ranking-environment-weight");environmentWeightControl.min="0";environmentWeightControl.max=String(Math.round(Number(rankingEnvironmentSettings.maximum_weight)*100));environmentWeightControl.step=String(Math.round(Number(rankingEnvironmentSettings.weight_step)*100));environmentWeightControl.value=String(Math.round(Number(rankingEnvironmentSettings.default_weight)*100));
function el(tag,text,className){const node=document.createElement(tag);if(text!==undefined)node.textContent=text;if(className)node.className=className;return node;}
function fmt(value,digits=1){return new Intl.NumberFormat("en-US",{minimumFractionDigits:digits,maximumFractionDigits:digits}).format(value);}
function brl(value,digits=2){return new Intl.NumberFormat("en-US",{style:"currency",currency:"BRL",minimumFractionDigits:digits,maximumFractionDigits:digits}).format(value);}
function pct(value){return fmt(100*value,1)+"%";}
function clamp(x,lo,hi){return Math.min(hi,Math.max(lo,x));}
function scoreOnTen(value,scale){const minimum=Number(rankingScoreSettings.minimum),maximum=Number(rankingScoreSettings.maximum),breakEven=Number(rankingScoreSettings.break_even),span=value<0?breakEven-minimum:maximum-breakEven,effectiveScale=Math.max(1e-9,Math.abs(Number(scale)||0));return clamp(breakEven+(value/effectiveScale)*span,minimum,maximum);}
function soilScoreOnTen(soc){return clamp(Number(soc)/Number(rankingEnvironmentSettings.soil_reference_g_kg)*Number(rankingScoreSettings.maximum),Number(rankingScoreSettings.minimum),Number(rankingScoreSettings.maximum));}
function waterMultiplierMean(counts){const multipliers=soilHypotheses.economic_yield_response.water_multiplier_by_class;let total=0,weighted=0;for(const [water,count] of Object.entries(counts||{})){const n=Number(count)||0,multiplier=Number(multipliers[water]);if(n>0&&Number.isFinite(multiplier)){total+=n;weighted+=n*multiplier;}}return total?weighted/total:Number(multipliers.water_medium)||1;}
function waterScoreOnTen(meanMultiplier){const multipliers=Object.values(soilHypotheses.economic_yield_response.water_multiplier_by_class).map(Number),scale=Math.max(...multipliers.map(value=>Math.abs(value-1)),1e-9);return scoreOnTen(Number(meanMultiplier)-1,scale);}
function waterDistributionSummary(counts,total){const entries=[["water_low","Baixa"],["water_medium","Média"],["water_high","Alta"]].filter(([id])=>Number(counts?.[id]||0)>0);return entries.map(([id,label])=>label+" "+pct(Number(counts[id])/Math.max(1,total))).join(" · ")||"sem observações";}
function soilCarbonClass(soc){const thresholds=soilHypotheses.soil_carbon.state_thresholds_g_kg;if(Number(soc)<Number(thresholds.low_max_exclusive))return "low";if(Number(soc)<Number(thresholds.medium_max_exclusive))return "medium";return "high";}
function soilStateId(soc){return {low:"soil_degraded",medium:"soil_regular",high:"soil_good"}[soilCarbonClass(soc)];}
function environmentCountFrame(){return {water:{water_low:0,water_medium:0,water_high:0},soil:{soil_degraded:0,soil_regular:0,soil_good:0}};}
function svgElement(name,attributes={}){const node=document.createElementNS("http://www.w3.org/2000/svg",name);for(const [key,value] of Object.entries(attributes))node.setAttribute(key,String(value));return node;}
function renderEnvironmentAreaChart(svgId,legendId,summaryId,countsByYear,dimension,series,completed){
  const svg=byId(svgId),legend=byId(legendId),summary=byId(summaryId),width=760,height=252,left=58,right=18,top=18,bottom=210,plotWidth=width-left-right,plotHeight=bottom-top;
  svg.replaceChildren();legend.replaceChildren();
  for(const item of series){const entry=el("span",undefined,"environment-legend-item"),swatch=el("i",undefined,"environment-legend-swatch");swatch.style.backgroundColor=item.color;entry.append(swatch,el("span",item.label));legend.append(entry);}
  const counts=countsByYear.map(frame=>frame?.[dimension]||{}),totals=counts.map(row=>series.reduce((sum,item)=>sum+Number(row[item.id]||0),0));
  if(!completed||totals.some(total=>total===0)){
    const message=svgElement("text",{x:width/2,y:height/2,"text-anchor":"middle"});message.textContent="Aguardando trajetórias";svg.append(message);summary.textContent="A distribuição aparece após a primeira prévia do Monte Carlo.";return;
  }
  const xAt=index=>left+plotWidth*index/(counts.length-1),yAt=fraction=>bottom-plotHeight*fraction;
  let lower=Array(counts.length).fill(0);
  for(const item of series){
    const upper=counts.map((row,index)=>lower[index]+Number(row[item.id]||0)/totals[index]);
    const topPath=upper.map((value,index)=>(index?"L":"M")+xAt(index).toFixed(2)+" "+yAt(value).toFixed(2)).join(" ");
    const bottomPath=lower.map((value,index)=>({value,index})).reverse().map(({value,index})=>"L"+xAt(index).toFixed(2)+" "+yAt(value).toFixed(2)).join(" ");
    const path=svgElement("path",{d:topPath+" "+bottomPath+" Z",fill:item.color,"fill-opacity":".94",stroke:"#ffffff","stroke-width":".8"});
    const title=svgElement("title");title.textContent=item.label+" · "+counts.map((row,index)=>"A"+index+" "+pct(Number(row[item.id]||0)/totals[index])).join(" · ");path.append(title);svg.append(path);lower=upper;
  }
  for(const value of [0,.25,.5,.75,1]){
    const y=yAt(value),line=svgElement("line",{x1:left,y1:y,x2:width-right,y2:y,stroke:"#ffffff","stroke-width":"1.2","stroke-opacity":".86"});svg.append(line);
    const label=svgElement("text",{x:left-9,y:y+3.5,"text-anchor":"end"});label.textContent=Math.round(value*100)+"%";svg.append(label);
  }
  for(let index=0;index<counts.length;index++){
    const tick=svgElement("line",{x1:xAt(index),y1:bottom,x2:xAt(index),y2:bottom+4,stroke:"#9aa69d"});svg.append(tick);
    const label=svgElement("text",{x:xAt(index),y:bottom+18,"text-anchor":"middle"});label.textContent="A"+index;svg.append(label);
  }
  const axisLabel=svgElement("text",{x:width-right,y:11,"text-anchor":"end"});axisLabel.textContent="% das trajetórias";svg.append(axisLabel);
  const last=counts.length-1,lastCount=totals[last],finalSummary=series.map(item=>{const count=Number(counts[last][item.id]||0);return item.label+" "+pct(count/lastCount)+" ("+count.toLocaleString("en-US")+")";}).join(" · ");
  summary.textContent="A5 · "+lastCount.toLocaleString("en-US")+" trajetórias · "+finalSummary+".";
}
function renderEnvironmentalDistributionCharts(countsByYear,completed){
  const thresholds=soilHypotheses.soil_carbon.state_thresholds_g_kg,soilSeries=[{id:"soil_good",label:"Bom (≥"+fmt(thresholds.high_min_inclusive,0)+" g/kg)",color:"#2eb78d"},{id:"soil_regular",label:"Regular ("+fmt(thresholds.low_max_exclusive,0)+"–<"+fmt(thresholds.medium_max_exclusive,0)+" g/kg)",color:"#e0ad25"},{id:"soil_degraded",label:"Degradado (<"+fmt(thresholds.low_max_exclusive,0)+" g/kg)",color:"#d96770"}],waterSeries=[{id:"water_high",label:"Alta",color:"#2eb78d"},{id:"water_medium",label:"Média",color:"#e0ad25"},{id:"water_low",label:"Baixa",color:"#d96770"}];
  renderEnvironmentAreaChart("soil-state-area-chart","soil-state-area-legend","soil-state-area-summary",countsByYear,"soil",soilSeries,completed);
  renderEnvironmentAreaChart("water-state-area-chart","water-state-area-legend","water-state-area-summary",countsByYear,"water",waterSeries,completed);
}
function seeded(seed){let s=(seed>>>0)||1;return function(){s+=0x6D2B79F5;let t=s;t=Math.imul(t^(t>>>15),t|1);t^=t+Math.imul(t^(t>>>7),t|61);return ((t^(t>>>14))>>>0)/4294967296;};}
function currentSeed(){return Math.max(0,Number.parseInt(byId("simulation-seed").value,10)||0);}
function cropStates(){return active.crop_markov.states;}
function cropStateMap(){if(cachedCropStateProfile!==active){cachedCropStatesById=Object.fromEntries(cropStates().map(state=>[state.id,state]));cachedCropStateProfile=active;}return cachedCropStatesById;}
function cropLabel(id){const state=cropStateMap()[id];return state?state.name:id;}
function cycleRule(cropId){return cropCycles.crops[cropId]||{cycle_days:365,maturation_days:365};}
function cycleDays(cropId){return Math.max(climatePeriodDays,Math.ceil(Number(cycleRule(cropId).cycle_days)/climatePeriodDays)*climatePeriodDays);}
function maturationDays(cropId){return Math.max(climatePeriodDays,Math.ceil(Number(cycleRule(cropId).maturation_days)/climatePeriodDays)*climatePeriodDays);}
function cropLifecycleRule(sourceId){return active.crop_markov.lifecycle_rules?.[sourceId]||null;}
function decendioForDay(day){let remaining=((Math.floor(day)%365)+365)%365;const monthDays=[31,28,31,30,31,30,31,31,30,31,30,31];for(let month=0;month<monthDays.length;month++){if(remaining<monthDays[month])return month*3+Math.floor(remaining/10)+1;remaining-=monthDays[month];}return 36;}
const monthStartDays=[0,31,59,90,120,151,181,212,243,273,304,334];
function decendioStartDay(decendio){const index=clamp(Number(decendio)-1,0,35),month=Math.floor(index/3),part=index%3;return monthStartDays[month]+part*10;}
function compactDecendioRanges(values){const sorted=[...new Set(values.map(Number).filter(value=>value>=1&&value<=36))].sort((a,b)=>a-b),ranges=[];for(const value of sorted){const last=ranges.at(-1);if(last&&value===last[1]+1)last[1]=value;else ranges.push([value,value]);}return ranges.map(([start,end])=>String(start).padStart(2,"0")+(start===end?"":"–"+String(end).padStart(2,"0"))).join(", ");}
function beanCalendarAuditNote(){const rows=(active?.zarc_planting_windows?.rows||[]).filter(row=>row.crop_parameter_id==="dry_bean"&&!/consorciad|consórcio|mistura/i.test(String(row.crop||""))),labels=[...new Set(rows.map(row=>String(row.crop||"")))],decendios=new Set();for(const row of rows)for(const risk of cropCycles.time_basis.planting_calendar.risk_levels_included_percent)for(const value of row.planting_decendios_by_risk_percent?.[String(risk)]||[])decendios.add(Number(value));const pamYears=(active?.crop_markov?.annual_sequence||[]).filter(year=>(year.top5_crops||[]).some(crop=>crop.state_id==="dry_bean")).length,totalYears=Number(active?.crop_markov?.annual_observation_count||0);return rows.length?" Feijão (estado Markov agregado): "+rows.length+" linhas MAPA standalone ("+labels.join(", ")+"); união municipal de risco 20/30/40: decêndios "+compactDecendioRanges([...decendios])+". Na PAM, esteve no top 5 de área em "+pamYears+"/"+totalYears+" anos. O calendário não distingue esses tipos/grupos no nó.":" Sem linha MAPA standalone de feijão neste perfil.";}
function decendioName(decendio){const index=clamp(Number(decendio)-1,0,35),month=Math.floor(index/3),part=index%3,months=["jan","fev","mar","abr","mai","jun","jul","ago","set","out","nov","dez"],monthEnds=[31,28,31,30,31,30,31,31,30,31,30,31],starts=[1,11,21][part],ends=part===2?monthEnds[month]:starts+9;return "decêndio "+String(index+1).padStart(2,"0")+" · "+String(starts).padStart(2,"0")+"–"+String(ends).padStart(2,"0")+"/"+months[month];}
function plantingWindowsByCrop(){
  if(cachedCalendarProfile===active&&cachedCropPlantingWindows)return cachedCropPlantingWindows;
  const windows={},officialCropIds=new Set(),basis={},rows=active?.zarc_planting_windows?.rows||[];
  for(const row of rows){
    const label=String(row.crop||"");if(/consorciad|consórcio|mistura/i.test(label))continue;
    const rawId=row.crop_parameter_id;if(!rawId)continue;
    const cropId=rawId;if(!cropStateMap()[cropId])continue;
    officialCropIds.add(cropId);
    for(const risk of cropCycles.time_basis.planting_calendar.risk_levels_included_percent){
      for(const decendio of row.planting_decendios_by_risk_percent?.[String(risk)]||[]){if(!windows[cropId])windows[cropId]=new Set();windows[cropId].add(Number(decendio));}
    }
  }
  const fallback=cropCycles.rotation_calendar_fallback||{},fallbackIds=new Set(fallback.crop_ids||[]),fallbackDecendios=fallback.all_year_decendios||[];
  for(const crop of cropStates()){
    if(officialCropIds.has(crop.id)){basis[crop.id]="official_zarc";continue;}
    if(fallbackIds.has(crop.id)){windows[crop.id]=new Set(fallbackDecendios);basis[crop.id]="all_season_rotation_fallback";continue;}
    basis[crop.id]="no_calendar_data";
  }
  cachedCalendarProfile=active;cachedCropPlantingWindows=windows;cachedPlantingDecendios=null;cachedCropCalendarBasis=basis;return windows;
}
function cropCalendarBasis(cropId){plantingWindowsByCrop();return cachedCropCalendarBasis?.[cropId]||"no_calendar_data";}
function cropCalendarBasisLabel(cropId){const basis=cropCalendarBasis(cropId);return basis==="official_zarc"?"MAPA ZARC oficial":basis==="all_season_rotation_fallback"?"hipótese de rotação: qualquer decêndio, sem linha ZARC":"sem calendário MAPA/fallback";}
function plantingWindowsByDecendio(){
  if(cachedCalendarProfile===active&&cachedPlantingDecendios)return cachedPlantingDecendios;
  const grouped=Array.from({length:37},()=>new Set());
  for(const [cropId,decendios] of Object.entries(plantingWindowsByCrop()))for(const decendio of decendios)grouped[decendio].add(cropId);
  cachedCalendarProfile=active;cachedPlantingDecendios=grouped;return grouped;
}
function eligibleCropDestinations(sourceId,day){
  const lifecycle=cropLifecycleRule(sourceId),allowed=cropAllowedDestinations(sourceId);
  if(lifecycle?.mode==="persistent_within_horizon")return allowed;
  // Annual calendars repeat every 365 days, so any nonempty window set has an opportunity within the next 365 days.
  if(cachedEligibleBySource?.has(sourceId))return cachedEligibleBySource.get(sourceId);
  const windows=plantingWindowsByCrop(),eligible=new Set([...allowed].filter(cropId=>windows[cropId]?.size));
  if(cachedEligibleBySource)cachedEligibleBySource.set(sourceId,eligible);
  return eligible;
}
function nextCropPlantingWindow(cropId,afterDay){
  const first=Math.max(0,Math.ceil(afterDay)),daysPerYear=Number(cropCycles.time_basis.days_per_year),limit=first+daysPerYear,decendios=plantingDecendiosForCrop(cropId);if(!decendios.length)return null;
  const firstYear=Math.floor(first/daysPerYear);
  for(let year=firstYear;year<=firstYear+1;year++)for(const decendio of decendios){
    const yearStart=year*daysPerYear,windowStart=yearStart+decendioStartDay(decendio),windowEnd=decendio===36?yearStart+daysPerYear:yearStart+decendioStartDay(decendio+1),day=Math.max(first,windowStart);
    if(day<windowEnd&&day<=limit)return {day,decendio,cropId};
  }
  return null;
}
let cachedCropDecendioProfile=null,cachedCropDecendios=null;
function plantingDecendiosForCrop(cropId){
  if(cachedCropDecendioProfile!==active){cachedCropDecendios=new Map();cachedCropDecendioProfile=active;}
  if(cachedCropDecendios.has(cropId))return cachedCropDecendios.get(cropId);
  const sorted=[...(plantingWindowsByCrop()[cropId]||[])].sort((a,b)=>a-b);cachedCropDecendios.set(cropId,sorted);return sorted;
}
function nextPlantingOpportunity(sourceId,afterDay){
  const first=Math.max(0,Math.ceil(afterDay)),daysPerYear=Number(cropCycles.time_basis.days_per_year),limit=first+daysPerYear,slots=plantingScheduleFor(sourceId),firstYear=Math.floor(first/daysPerYear);
  for(let year=firstYear;year<=firstYear+1;year++)for(const slot of slots){
    const yearStart=year*daysPerYear,windowStart=yearStart+decendioStartDay(slot.decendio),windowEnd=slot.decendio===36?yearStart+daysPerYear:yearStart+decendioStartDay(slot.decendio+1),day=Math.max(first,windowStart);
    if(day<windowEnd&&day<=limit)return {day,decendio:slot.decendio,destinations:slot.destinations};
  }
  return null;
}
function cropAllowedDestinations(sourceId){
  if(cachedAllowedProfile!==active){cachedAllowedBySource=new Map();cachedAllowedProfile=active;cachedEligibleBySource=new Map();}
  if(cachedAllowedBySource.has(sourceId))return cachedAllowedBySource.get(sourceId);
  const allowed=new Set(active.crop_markov.transitions.filter(edge=>edge.from===sourceId).map(edge=>edge.to));
  cachedAllowedBySource.set(sourceId,allowed);return allowed;
}
function plantingScheduleFor(sourceId){
  if(cachedScheduleProfile!==active){cachedPlantingSchedules=new Map();cachedScheduleProfile=active;}
  if(cachedPlantingSchedules.has(sourceId))return cachedPlantingSchedules.get(sourceId);
  const allowed=sourceId==="sugarcane"?sugarcaneReformDestinations():cropAllowedDestinations(sourceId);
  const grouped=plantingWindowsByDecendio(),slots=[];
  for(let decendio=1;decendio<=36;decendio++){const destinations=new Set([...grouped[decendio]].filter(cropId=>allowed.has(cropId)));if(destinations.size)slots.push({decendio,destinations});}
  cachedPlantingSchedules.set(sourceId,slots);return slots;
}
function sugarcaneReformDestinations(){
  return new Set(cropStates().filter(({id})=>{
    const kind=cycleRule(id).class;
    return (kind==="annual"||kind==="cover_or_annual")&&plantingDecendiosForCrop(id).length>0;
  }).map(({id})=>id));
}
function selectedGraphPlantingDay(){return decendioStartDay(Number(byId("matrix-planting-decendio")?.value||1))+4;}
function outgoingCount(stateId){return active.crop_markov.transitions.filter(row=>row.from===stateId).reduce((maximum,row)=>Math.max(maximum,Number(row.outgoing_mass??0)),0);}
function cropTransitionMap(){if(cachedCropTransitionProfile!==active){cachedCropTransitions=new Map(active.crop_markov.transitions.map(row=>[row.from+"|"+row.to,row]));cachedCropTransitionProfile=active;}return cachedCropTransitions;}
function pamMass(from,to){const edge=cropTransitionMap().get(from+"|"+to);return edge?Number(edge.mass??0):0;}
function dominantObservedCount(from,to){const edge=cropTransitionMap().get(from+"|"+to);return edge?Number(edge.count||0):0;}
function dominantOutgoingCount(stateId){return active.crop_markov.transitions.filter(row=>row.from===stateId).reduce((maximum,row)=>Math.max(maximum,Number(row.outgoing_count||0)),0);}
function alpha(){return active.crop_markov.alpha_per_destination;}
function eligiblePamMass(sourceId,allowed){return[...allowed].reduce((sum,destinationId)=>sum+pamMass(sourceId,destinationId),0);}
function cropBaseProbability(sourceId,destinationId,allowed){if(!allowed.has(destinationId))return 0;const count=eligiblePamMass(sourceId,allowed);return(pamMass(sourceId,destinationId)+alpha())/(count+allowed.size*alpha()||1);}

function renderCropTimeline(){
  const root=byId("crop-timeline");root.replaceChildren();
  for(const year of active.crop_markov.annual_sequence){
    const chip=el("div",undefined,"year-chip");
    const topFive=year.top5_crops||[{state_id:year.state_id,crop_name:year.crop_name,harvested_area_ha:year.harvested_area_ha,area_share_within_top5:1}],summary=topFive.map(item=>(item.crop_name||cropLabel(item.state_id))+" "+pct(Number(item.area_share_within_top5||0))).join(" · ");
    chip.append(el("strong",String(year.year)),el("span",summary));
    chip.title="Top 5 PAM entre os produtos mapeados; pesos pela participação na área top 5. "+topFive.map(item=>item.rank+"º "+(item.crop_name||cropLabel(item.state_id))+": "+fmt(item.harvested_area_ha,0)+" ha ("+pct(item.area_share_within_top5)+")").join(" · ");
    root.append(chip);
  }
}

function cropEnvironmentalFactors(crop,waterId,soc){
  const params=soilHypotheses.probability_modifiers;
  const waterFraction=typeof waterId==="number"?waterId:Number(params.water_state_representative_fraction[waterId]??0.5);
  const kcValues=cropStates().map(item=>item.kc_annual_effective).filter(value=>Number.isFinite(value));
  const meanKc=kcValues.reduce((a,b)=>a+b,0)/(kcValues.length||1);
  const kc=Number.isFinite(crop.kc_annual_effective)?crop.kc_annual_effective:meanKc;
  const waterAlignment=clamp((waterFraction-Number(params.water_reference_fraction??0.5))/Number(params.water_span_fraction??0.3),-1,1);
  const waterFactor=Math.exp(Number(params.water_log_weight_coefficient)*waterAlignment*(kc-meanKc));
  const soil=soilHypotheses.soil_carbon;
  const deficit=clamp((Number(params.soil_carbon_reference_g_kg)-soc)/Number(params.soil_carbon_deficit_span_g_kg),0,1);
  const range=soil.delta_by_crop[crop.id]||[0,0];
  const deltaMean=(Number(range[0])+Number(range[1]))/2;
  const soilFactor=Math.exp(Number(params.soil_log_weight_coefficient)*deficit*(deltaMean/0.2));
  return {waterFactor,soilFactor,waterAlignment,soilDeficit:deficit};
}

function cropProbabilities(sourceId,waterId,soc,baseWeights=null,eligibleDestinations=null){
  const allowed=eligibleDestinations?new Set(eligibleDestinations):cropAllowedDestinations(sourceId);
  if(!baseWeights)return Object.fromEntries(Object.entries(cropProbabilitySummary(sourceId,waterId,soc,1200,allowed)).map(([id,summary])=>[id,summary.mean]));
  const crops=cropStates(),weights={};
  for(const dest of crops){
    if(!allowed.has(dest.id)){weights[dest.id]=0;continue;}
    const base=Number(baseWeights[dest.id]||0);
    const factors=cropEnvironmentalFactors(dest,waterId,soc);
    weights[dest.id]=base*factors.waterFactor*factors.soilFactor;
  }
  const total=Object.values(weights).reduce((a,b)=>a+b,0)||1;
  return Object.fromEntries(Object.entries(weights).map(([id,value])=>[id,value/total]));
}

function cropProbabilitySummary(sourceId,waterId,soc,samples=1200,eligibleDestinations=null){
  const allowed=eligibleDestinations?new Set(eligibleDestinations):cropAllowedDestinations(sourceId);
  const cacheKey=[active?.crop_markov?.source?.municipality_ibge_code,sourceId,waterId,Number(soc).toFixed(1),samples,[...allowed].sort().join(",")].join("|");
  if(graphIntervalCache.has(cacheKey))return graphIntervalCache.get(cacheKey);
  let hash=2166136261;for(const char of cacheKey){hash^=char.charCodeAt(0);hash=Math.imul(hash,16777619);}
  const rng=seeded(hash),crops=cropStates(),values=Object.fromEntries(crops.map(crop=>[crop.id,[]]));
  for(let sample=0;sample<samples;sample++){
    const weights={};let total=0;
    for(const dest of crops){if(!allowed.has(dest.id)){weights[dest.id]=0;continue;}const factor=cropEnvironmentalFactors(dest,waterId,soc),weight=gammaRandom(pamMass(sourceId,dest.id)+alpha(),rng)*factor.waterFactor*factor.soilFactor;weights[dest.id]=weight;total+=weight;}
    for(const dest of crops)values[dest.id].push(total?weights[dest.id]/total:0);
  }
  const result=Object.fromEntries(crops.map(crop=>{const draws=values[crop.id];return[crop.id,{mean:draws.reduce((sum,value)=>sum+value,0)/draws.length,lower:quantile(draws,.05),upper:quantile(draws,.95)}];}));
  if(graphIntervalCache.size>80)graphIntervalCache.clear();graphIntervalCache.set(cacheKey,result);return result;
}

function svgNode(tag,attributes={}){
  const node=document.createElementNS("http://www.w3.org/2000/svg",tag);for(const [key,value] of Object.entries(attributes))node.setAttribute(key,String(value));return node;
}
function blendColor(from,to,fraction){
  const a=from.match(/[a-f0-9]{2}/gi).map(value=>parseInt(value,16)),b=to.match(/[a-f0-9]{2}/gi).map(value=>parseInt(value,16));
  return "#"+a.map((value,index)=>Math.round(value+(b[index]-value)*clamp(fraction,0,1)).toString(16).padStart(2,"0")).join("");
}
function renderCropGraph(waterId,soc,nodeCountsByYear={},edgeCountsByYear={},completedTrajectories=0){
  if(!active)return;
  const plantingDay=selectedGraphPlantingDay(),plantingDecendio=decendioForDay(plantingDay);
  const states=cropStates(),countNodes=byId("crop-graph-nodes"),countEdges=byId("crop-graph-edges"),countLabels=byId("crop-graph-edge-labels"),yearSelect=byId("graph-year-select");
  const fullCycle=yearSelect.value==="all",year=Math.max(0,Number(yearSelect.value)||0),sumYears=source=>{const result={};for(let index=1;index<=horizon;index++)for(const [key,value] of Object.entries(source[index]||{}))result[key]=(result[key]||0)+Number(value);return result;},nodeCounts=fullCycle?sumYears(nodeCountsByYear):(nodeCountsByYear[year]||{}),edgeCounts=fullCycle?sumYears(edgeCountsByYear):(edgeCountsByYear[year]||{}),graphScope=fullCycle?"ciclo completo · 5 anos":year===0?"estado inicial":"ano "+year,nodeDenominator=completedTrajectories*(fullCycle?horizon:1),maxCount=Math.max(1,...Object.values(nodeCounts).map(Number));
  selectedGraphCropId=states.some(state=>state.id===selectedGraphCropId)?selectedGraphCropId:states.find(state=>state.initial_selectable)?.id||states[0]?.id;
  const selected=states.find(state=>state.id===selectedGraphCropId),positions=new Map();
  const probabilitySummaries=cropProbabilitySummary(selectedGraphCropId,waterId,soc,1200,eligibleCropDestinations(selectedGraphCropId,plantingDay));
  states.forEach((state,index)=>{const angle=-Math.PI/2+index*2*Math.PI/states.length;positions.set(state.id,{x:500+300*Math.cos(angle),y:400+300*Math.sin(angle),index});});
  countNodes.replaceChildren();countEdges.replaceChildren();countLabels.replaceChildren();
  const transitions=[];
  for(const source of states){
    const allowed=eligibleCropDestinations(source.id,plantingDay),probabilities=cropProbabilities(source.id,waterId,soc,null,allowed),sourceTotal=outgoingCount(source.id),eligibleTotal=eligiblePamMass(source.id,allowed),lifecycle=cropLifecycleRule(source.id);
    for(const destination of states){const factors=cropEnvironmentalFactors(destination,waterId,soc),posterior=source.id===selectedGraphCropId?probabilitySummaries[destination.id]:null;transitions.push({source,destination,probability:Number(posterior?.mean??probabilities[destination.id]??0),interval:posterior,observed:pamMass(source.id,destination.id),dominantObserved:dominantObservedCount(source.id,destination.id),sourceTotal,eligibleTotal,dominantSourceTotal:dominantOutgoingCount(source.id),eligibleCount:allowed.size,baseProbability:cropBaseProbability(source.id,destination.id,allowed),waterFactor:factors.waterFactor,soilFactor:factors.soilFactor,calendarBasis:cropCalendarBasis(destination.id),lifecycleOverride:!allowed.has(destination.id),lifecycle});}
  }
  for(const edge of transitions){
    const start=positions.get(edge.source.id),end=positions.get(edge.destination.id),isOutgoing=edge.source.id===selectedGraphCropId,dx=end.x-start.x,dy=end.y-start.y,length=Math.max(1,Math.hypot(dx,dy));
    let d,labelX,labelY;
    if(edge.source.id===edge.destination.id){
      d="M "+(start.x-18)+" "+(start.y-27)+" C "+(start.x-55)+" "+(start.y-82)+", "+(start.x+55)+" "+(start.y-82)+", "+(start.x+18)+" "+(start.y-27);
      labelX=start.x;labelY=start.y-73;
    }else{
      const ux=dx/length,uy=dy/length,sx=start.x+ux*67,sy=start.y+uy*34,ex=end.x-ux*67,ey=end.y-uy*34,step=(end.index-start.index+states.length)%states.length,lane=step<=states.length/2?step:step-states.length,curve=lane*9;
      const cx=(sx+ex)/2-(ey-sy)/length*curve,cy=(sy+ey)/2+(ex-sx)/length*curve;
      d="M "+sx+" "+sy+" Q "+cx+" "+cy+" "+ex+" "+ey;
      const t=.79,u=1-t;labelX=u*u*sx+2*u*t*cx+t*t*ex;labelY=u*u*sy+2*u*t*cy+t*t*ey-4;
    }
    const path=svgNode("path",{d,class:"graph-edge"+(isOutgoing?" is-outgoing":"")+(edge.lifecycleOverride?" lifecycle-blocked":""),"stroke-width":isOutgoing?1.2+8*Math.sqrt(edge.probability):.7+2*Math.sqrt(edge.probability),"marker-end":"url(#crop-arrow)"});
    const edgeCount=Number(edgeCounts[edge.source.id+"|"+edge.destination.id]||0),outgoingEvents=Object.entries(edgeCounts).filter(([key])=>key.startsWith(edge.source.id+"|")).reduce((sum,[,value])=>sum+Number(value),0),edgeFrequency=outgoingEvents?edgeCount/outgoingEvents:0;
    const interval=edge.interval||{lower:edge.probability,upper:edge.probability},calendarNote=edge.calendarBasis==="official_zarc"?"; calendário: janela oficial MAPA (grupos/códigos agregados)":edge.calendarBasis==="all_season_rotation_fallback"?"; calendário: hipótese de cobertura de rotação, qualquer decêndio, sem linha ZARC":"; calendário: sem dado ZARC ou hipótese de rotação",blockedNote=edge.lifecycleOverride?"; bloqueada por regra perene ou falta de janela elegível no próximo ano":"",title=svgNode("title");title.textContent=edge.source.name+" → "+edge.destination.name+": P média contextual "+fmt(100*edge.probability,2)+"%; intervalo Dirichlet 90% "+fmt(100*interval.lower,2)+"–"+fmt(100*interval.upper,2)+"%; P₀ top-5=(massa ponderada + α)/(suporte ponderado + α×destinos)="+fmt(100*edge.baseProbability,2)+"%; massa top-5 "+fmt(edge.observed,3)+"/"+fmt(edge.sourceTotal,3)+" unidades esperadas, suporte elegível="+fmt(edge.eligibleTotal,3)+(edge.probability>0&&edge.observed===0?"; apenas prior Dirichlet":"")+"; rank 1 observado "+edge.dominantObserved+"/"+edge.dominantSourceTotal+" pares, α="+fmt(alpha(),1)+" por destino; fatores água/solo "+fmt(edge.waterFactor,3)+"/"+fmt(edge.soilFactor,3)+calendarNote+blockedNote+"; Monte Carlo no "+graphScope+": "+edgeCount+" decisões/transições ("+fmt(100*edgeFrequency,1)+"% das saídas deste nó).";path.append(title);countEdges.append(path);
    if(isOutgoing){const label=svgNode("text",{x:labelX,y:labelY,class:"graph-edge-label"});label.textContent=fmt(100*edge.probability,2)+"%";countLabels.append(label);}
  }
  for(const state of states){
    const point=positions.get(state.id),count=Number(nodeCounts[state.id]||0),frequency=nodeDenominator?count/nodeDenominator:0,relative=count/maxCount,group=svgNode("g",{class:"graph-node"+(state.id===selectedGraphCropId?" is-selected":""),transform:"translate("+point.x+" "+point.y+")",role:"button",tabindex:"0","aria-label":state.name+", frequência Monte Carlo no "+graphScope+" de "+pct(frequency)+(state.id===selectedGraphCropId?", nó selecionado":"")});
    const rect=svgNode("rect",{x:-63,y:-30,width:126,height:60,rx:13,fill:blendColor("#edf2ed","#377a4e",relative*.85)}),name=svgNode("text",{x:0,y:-4,class:"graph-node-name",fill:relative>.58?"#fff":"#26382b"}),frequencyText=svgNode("text",{x:0,y:15,class:"graph-node-frequency",fill:relative>.58?"#f2f8f3":"#58695d"});
    name.textContent=state.name;frequencyText.textContent="MC "+pct(frequency)+" · n="+count.toLocaleString("en-US");
    const title=svgNode("title");title.textContent=state.name+" · P(MC "+graphScope+")="+pct(frequency)+(state.initial_selectable?" · cultura inicial permitida":" · destino de transição");group.append(rect,name,frequencyText,title);
    group.addEventListener("click",()=>{selectedGraphCropId=state.id;renderCropGraph(waterId,soc,nodeCountsByYear,edgeCountsByYear,completedTrajectories);});
    group.addEventListener("keydown",event=>{if(event.key==="Enter"||event.key===" "){event.preventDefault();selectedGraphCropId=state.id;renderCropGraph(waterId,soc,nodeCountsByYear,edgeCountsByYear,completedTrajectories);}});
    countNodes.append(group);
  }
  const outgoing=transitions.filter(edge=>edge.source.id===selectedGraphCropId).sort((a,b)=>b.probability-a.probability),totalAtNode=Number(nodeCounts[selectedGraphCropId]||0),sideTitle=byId("graph-selected-title"),sideContext=byId("graph-selected-context"),sideList=byId("graph-edge-list");
  sideTitle.textContent="Saídas de "+(selected?.name||"—");
  const lifecycle=cropLifecycleRule(selectedGraphCropId),mcState=(completedTrajectories?"amostra parcial "+completedTrajectories.toLocaleString("en-US")+"/"+maxTrajectories.toLocaleString("en-US"):"simulação ainda não iniciada"),occupied=Object.values(nodeCounts).reduce((sum,value)=>sum+Number(value||0),0),fallowPositions=Math.max(0,nodeDenominator-occupied);
  sideContext.textContent=graphScope+": "+mcState+" · "+pct(nodeDenominator?totalAtNode/nodeDenominator:0)+" das posições observadas ocupam este nó (n="+totalAtNode.toLocaleString("en-US")+" de "+nodeDenominator.toLocaleString("en-US")+" posições). Pousio no fechamento: "+fallowPositions.toLocaleString("en-US")+" posições ("+pct(nodeDenominator?fallowPositions/nodeDenominator:0)+"). As transições PAM usam o produto das participações top-5 entre anos consecutivos, com independência assumida entre áreas municipais; não são trocas observadas no mesmo talhão. A probabilidade ajusta essa massa com prior Dirichlet, ambiente e calendário MAPA ou hipótese explícita de cobertura no "+decendioName(plantingDecendio)+". Água "+waterLabels[waterId].toLowerCase()+" e carbono "+fmt(soc,1)+" g/kg ajustam os pesos; intervalo de 90% sorteia linhas Dirichlet. A cultura escolhida pode esperar a próxima janela aplicável para ser semeada."+(lifecycle?" Regra de ciclo: "+lifecycle.rationale:"");
  sideList.replaceChildren();
  for(const edge of outgoing){const edgeCount=Number(edgeCounts[edge.source.id+"|"+edge.destination.id]||0),outgoingEvents=Object.entries(edgeCounts).filter(([key])=>key.startsWith(edge.source.id+"|")).reduce((sum,[,value])=>sum+Number(value),0),mcShare=outgoingEvents?edgeCount/outgoingEvents:0,interval=edge.interval||{lower:edge.probability,upper:edge.probability},li=document.createElement("li"),strong=el("strong","→ "+edge.destination.name+" · P média "+fmt(100*edge.probability,2)+"%"),ruleNote=edge.lifecycleOverride?" · bloqueada por janela/regra perene":"",small=el("small","Calendário: "+cropCalendarBasisLabel(edge.destination.id)+" · Dirichlet 90%: "+fmt(100*interval.lower,2)+"–"+fmt(100*interval.upper,2)+"% · P₀ top-5 "+fmt(100*edge.baseProbability,2)+"% (α="+fmt(alpha(),1)+") · massa top-5 "+fmt(edge.observed,3)+"/"+fmt(edge.sourceTotal,3)+" eq. · rank 1 PAM "+edge.dominantObserved+"/"+edge.dominantSourceTotal+" · água/solo "+fmt(edge.waterFactor,3)+"/"+fmt(edge.soilFactor,3)+ruleNote+" · MC no "+graphScope+": "+edgeCount+"/"+outgoingEvents+" saídas ("+pct(mcShare)+")");li.append(strong,document.createElement("br"),small);sideList.append(li);}
  byId("graph-environment").textContent="Ambiente da decisão: "+decendioName(plantingDecendio)+" · destinos com janela MAPA ou hipótese aplicável nos próximos 365 dias · água "+waterLabels[waterId].toLowerCase()+" · carbono "+fmt(soc,1)+" g/kg · origem selecionada: "+(selected?.name||"—");
}

function renderCropMatrix(){
  const table=byId("crop-matrix");table.replaceChildren();
  const states=cropStates(),waterId=byId("matrix-water-select").value||"water_medium",soc=Number(byId("matrix-carbon-input").value)||0,plantingDay=selectedGraphPlantingDay(),plantingDecendio=decendioForDay(plantingDay);
  const thead=document.createElement("thead"),headRow=document.createElement("tr");
  headRow.append(el("th","Origem ↓ · próximo destino →","corner"));
  for(const state of states){const th=el("th",state.name);th.scope="col";th.title=(state.initial_selectable?"Cultura inicial permitida":"Candidata de transição")+" · Kc efetivo anual: "+(Number.isFinite(state.kc_annual_effective)?fmt(state.kc_annual_effective,2):"sem curva, fator hídrico neutro")+" · "+state.kc_annual_support;headRow.append(th);}
  thead.append(headRow);table.append(thead);
  const tbody=document.createElement("tbody");
  for(const source of states){
    const row=document.createElement("tr"),rowHead=el("th",undefined);rowHead.scope="row";
    const allowed=eligibleCropDestinations(source.id,plantingDay),n=eligiblePamMass(source.id,allowed),stateNode=el("div",source.name,"matrix-state");
    stateNode.append(el("small","Top-5 PAM · suporte elegível="+fmt(n,2)+" eq. · rank 1 n="+dominantOutgoingCount(source.id)+(source.initial_selectable?" · início permitido":"")));
    rowHead.append(stateNode);row.append(rowHead);
    const probabilities=cropProbabilities(source.id,waterId,soc,null,allowed);
    for(const dest of states){
      const td=document.createElement("td"),count=pamMass(source.id,dest.id),dominantCount=dominantObservedCount(source.id,dest.id),probability=probabilities[dest.id];
      const cell=el("div",undefined,"cell-content"+((n<5)?" matrix-low-support":""));
      cell.append(el("strong",pct(probability)),el("span",fmt(count,2)+"/"+fmt(n,2)+" massa"),el("span",allowed.has(dest.id)&&count===0?"Só prior":"rank 1: "+dominantCount));
      cell.title=allowed.has(dest.id)?"P ajustada por água/solo e condicionada à decisão no "+decendioName(plantingDecendio)+"; calendário: "+cropCalendarBasisLabel(dest.id)+". Massa de transição top-5 ponderada: "+fmt(count,4)+"/"+fmt(n,4)+" unidades esperadas sob independência de marginais municipais; pares rank 1 observados: "+dominantCount+". Prior Dirichlet: "+alpha()+" por destino elegível.":"Destino bloqueado no contexto: calendário "+cropCalendarBasisLabel(dest.id)+" ou regra perene; a aresta não é sorteada.";
      td.append(cell);row.append(td);
    }
    tbody.append(row);
  }
  table.append(tbody);
  byId("crop-matrix-note").textContent="Matriz completa: "+states.length+" estados de cultura. A evidência é a massa fracionária de transições construída com as participações de área PAM do top 5 em anos consecutivos, sob independência assumida; o número rank 1 fica separado como diagnóstico. Contexto: decisão no "+decendioName(plantingDecendio)+" · água "+waterLabels[waterId].toLowerCase()+" · carbono "+fmt(soc,1)+" g/kg. As probabilidades são condicionais a uma janela MAPA ou à hipótese explicitamente marcada de calendário para cobertura sem dado. Células âmbar têm suporte efetivo baixo; destinos sem calendário aplicável aparecem em 0%.";
  renderCropGraph(waterId,soc,latestRun?.nodeCountsByYear||{},latestRun?.edgeCountsByYear||{},latestRun?.completed||0);

}


function renderWaterMatrix(){
  const table=byId("water-matrix");table.replaceChildren();
  const states=active.water_markov.states,thead=document.createElement("thead"),head=document.createElement("tr");
  head.append(el("th","Água atual × chuva","corner"));
  for(const state of states)head.append(el("th",state.label));
  thead.append(head);table.append(thead);
  const tbody=document.createElement("tbody");
  for(const environment of ["dry","normal","wet"]){
    for(const source of states){
      const modelRow=active.water_markov.transitions.find(row=>row.from===source.id&&row.environment===environment);
      const n=modelRow?modelRow.effective_sample_size:0,row=document.createElement("tr"),th=el("th",source.label+" · chuva "+rainLabels[environment]+" · n="+n);th.scope="row";row.append(th);
      for(const destination of states){
        const count=modelRow?Number(modelRow.counts[destination.id]||0):0,td=document.createElement("td");
        if(!n)td.append(el("span","sem dados","matrix-zero"));
        else{const cell=el("div",undefined,"cell-content"+(n<30?" matrix-low-support":""));cell.append(el("strong",count+"/"+n),el("span",pct(count/n)));td.append(cell);}
        row.append(td);
      }
      tbody.append(row);
    }
  }
  table.append(tbody);
}

function renderVplReferences(){
  const snapshot=economicData.price_snapshot;
  byId("vpl-status").textContent="Critério econômico: maximizar o VPL por hectare em 60 meses, com ciclos e maturação por cultura, fluxos descontados pela data e probabilidade da rota exibida separadamente.";
  byId("economic-price-source").textContent="Yahoo Finance · fechamento de "+snapshot.as_of_date+" · futuros CBOT de soja e milho convertidos para R$/t pela PTAX. São uma referência de bolsa ao lado da mediana PAM real; não substituem o preço local usado como base.";
  const table=byId("economic-price-table"),head=document.createElement("thead"),headRow=document.createElement("tr"),body=document.createElement("tbody");
  for(const label of ["Cultura","Contrato","Data","Fechamento (R$/t)"]){const th=el("th",label);headRow.append(th);}head.append(headRow);table.replaceChildren(head,body);
  const cropNames={soybean:"Soja",maize:"Milho"};
  for(const quote of snapshot.quotes){const row=document.createElement("tr"),contractCell=document.createElement("td"),link=el("a",quote.symbol+" · "+quote.contract_name);link.href=quote.source_url;link.target="_blank";link.rel="noreferrer";contractCell.append(link);row.append(el("td",cropNames[quote.crop]||quote.crop),contractCell,el("td",quote.quote_date),el("td",brl(quote.price_brl_per_metric_ton)+"/t"));body.append(row);}
}

function gammaRandom(shape,rng){
  if(shape<1)return gammaRandom(shape+1,rng)*Math.pow(Math.max(rng(),1e-12),1/shape);
  const d=shape-1/3,c=1/Math.sqrt(9*d);
  while(true){
    let u=0,v=0;while(u===0)u=rng();while(v===0)v=rng();
    const x=Math.sqrt(-2*Math.log(u))*Math.cos(2*Math.PI*v),base=1+c*x;
    if(base<=0)continue;
    const cube=base*base*base,draw=rng();
    if(draw<1-0.0331*x*x*x*x||Math.log(draw)<0.5*x*x+d*(1-cube+Math.log(cube)))return d*cube;
  }
}
function sampleCropRow(sourceId,rng,allowed=cropAllowedDestinations(sourceId),reform=false){
  const weights={};let total=0;
  for(const dest of cropStates()){
    if(!allowed.has(dest.id)){weights[dest.id]=0;continue;}
    const mass=reform?(active.crop_markov.sugarcane_reform_pam_mass[dest.id]??0):pamMass(sourceId,dest.id);
    const value=gammaRandom(mass+alpha(),rng);weights[dest.id]=value;total+=value;
  }
  return Object.fromEntries(Object.entries(weights).map(([id,value])=>[id,value/total]));
}
function drawProbability(probabilities,rng){
  let draw=rng();for(const [id,p] of Object.entries(probabilities)){draw-=p;if(draw<0)return id;}return Object.keys(probabilities).at(-1)||null;
}
function waterTransitionRow(state,environment){
  if(cachedWaterProfile!==active){cachedWaterRows=new Map();cachedWaterProfile=active;}
  const key=state+"|"+environment;if(cachedWaterRows.has(key))return cachedWaterRows.get(key);
  const modelRow=active.water_markov.transitions.find(row=>row.from===state&&row.environment===environment);
  if(!modelRow){cachedWaterRows.set(key,null);return null;}
  const rows=[];let total=0;
  for(const item of active.water_markov.states){const count=Number(modelRow.counts[item.id]||0);if(count>0){rows.push([item.id,count]);total+=count;}}
  const cached={rows,total};cachedWaterRows.set(key,cached);return cached;
}
function sampleWaterNext(state,environment,rng){
  const cached=waterTransitionRow(state,environment);if(!cached||cached.total<=0)return state;
  let draw=rng()*cached.total;for(const [destination,count] of cached.rows){draw-=count;if(draw<0)return destination;}return cached.rows.at(-1)?.[0]||state;
}
function advanceWaterForCrop(state,environment,cropId,rng){
  const sampled=sampleWaterNext(state,environment,rng),crop=cropStateMap()[cropId];
  const annualKc=Number.isFinite(crop?.kc_annual_effective)?crop.kc_annual_effective:Number(soilHypotheses.probability_modifiers.water_reference_kc);
  const etoPerPeriod=Number(active.climate_summary.mean_annual_eto_mm)/active.water_markov.periods_per_year;
  const awc=Math.max(1,Number(active.soil.available_water_capacity_mm));
  const demandShift=(annualKc-Number(soilHypotheses.probability_modifiers.water_reference_kc))*etoPerPeriod/awc;
  const referenceFraction=Number(soilHypotheses.probability_modifiers.water_state_representative_fraction[sampled]??0.5);
  return clamp(referenceFraction-demandShift,0,1);
}
function waterClass(fraction){
  const thresholds=active.water_classes;
  if(fraction<=Number(thresholds.low_max_inclusive))return "water_low";
  if(fraction<=Number(thresholds.medium_max_inclusive))return "water_medium";
  return "water_high";
}
function soilDelta(cropId,rng){
  const range=soilHypotheses.soil_carbon.delta_by_crop[cropId]||[0,0];
  return Number(range[0])+rng()*(Number(range[1])-Number(range[0]));
}
function repeatedCropYieldMultiplier(cropId,consecutivePlantings){
  const effect=cropCycles.repeated_crop_effect||{},cropEffect=effect.crop_specific?.[cropId]||effect,classes=effect.applies_to_classes||[];
  if(!classes.includes(cycleRule(cropId).class))return 1;
  const repeats=Math.max(0,Number(consecutivePlantings||1)-1),perRepeat=Math.max(0,Number(cropEffect.yield_penalty_per_consecutive_replant_fraction||0)),cap=clamp(Number(cropEffect.maximum_yield_penalty_fraction||0),0,1);
  return Math.max(1-cap,1-repeats*perRepeat);
}
function sampleTrajectory(startCrop,rng,environmentYears,initialSugarcaneCut=1){
  const posteriorRows={},historyBlocks=Array.from({length:horizon},()=>environmentYears[Math.floor(rng()*environmentYears.length)]),path=[],annualPath=[],soilRates={};
  let crop=startCrop,lastMainCrop=startCrop,consecutivePlantings=1;
  let nextSugarcaneCut=startCrop==="sugarcane"?initialSugarcaneCut:1;
  let waterFraction=active.water_markov.initial_storage_fraction,water=waterClass(waterFraction),soc=active.soil.organic_carbon_top_0_30_g_kg,mainTimer=cycleDays(crop),maturityRemaining=0,formationTimer=Infinity,pendingPlanting=null;
  const daysPerYear=Number(cropCycles.time_basis.days_per_year),yearStates=Array(horizon+1),environmentPath=Array(horizon+1);
  const rateFor=id=>{if(!id)return 0;if(!soilRates[id])soilRates[id]=soilDelta(id,rng);return soilRates[id];};
  path.push({day:0,year:0,crop,water,waterFraction,soc,eventKind:"start"});yearStates[0]={crop};environmentPath[0]={water,waterFraction,soc};
  const periodCount=Math.round(horizonDays/climatePeriodDays);
  for(let period=0;period<periodCount;period++){
    const day=period*climatePeriodDays,yearIndex=Math.min(horizon-1,Math.floor(day/daysPerYear)),periodInYear=period%Number(cropCycles.time_basis.environment_periods_per_year),climate=historyBlocks[yearIndex][1][periodInYear];
    waterFraction=advanceWaterForCrop(water,climate,crop,rng);
    water=waterClass(waterFraction);
    soc=Math.max(0.1,soc+rateFor(crop)*climatePeriodDays/daysPerYear);
    mainTimer-=climatePeriodDays;if(maturityRemaining>0)maturityRemaining-=climatePeriodDays;if(Number.isFinite(formationTimer))formationTimer-=climatePeriodDays;
    const eventDay=Math.round((period+1)*climatePeriodDays*1e9)/1e9;
    const eventYear=Math.min(horizon,Math.ceil(eventDay/daysPerYear));
    // An annual cycle is exactly 24 climate steps. Subtraction can leave a tiny positive remainder.
    if(crop&&mainTimer<=1e-9){
      const harvested=crop,perennial=Boolean(cropLifecycleRule(harvested)),harvest={day:eventDay,year:eventYear,crop:harvested,water,waterFraction,soc,eventKind:"main_harvest",flowKind:"main_harvest",flowCrop:harvested,consecutivePlantings,repeatYieldMultiplier:repeatedCropYieldMultiplier(harvested,consecutivePlantings),cycleDays:cycleDays(harvested),climateYear:historyBlocks[yearIndex][0]};
      const caneCut=harvested==="sugarcane"?nextSugarcaneCut++:null;
      if(caneCut!==null)harvest.sugarcane_cut=caneCut;
      path.push(harvest);
      const reform=caneCut===cycleRule("sugarcane").modeled_harvest_cuts;
      if(perennial&&!reform){
        path.push({day:eventDay,year:eventYear,crop:harvested,fromCrop:harvested,water,soc,transitionProbability:1,eventKind:"main_transition",transitionReason:"colheita recorrente de cultura perene"});
        mainTimer=cycleDays(harvested);maturityRemaining=0;formationTimer=Infinity;
      }else{
        lastMainCrop=harvested;crop=null;mainTimer=Infinity;maturityRemaining=0;formationTimer=Infinity;
        pendingPlanting=reform&&eventDay>=horizonDays?null:nextPlantingOpportunity(lastMainCrop,eventDay);
        if(reform)path.push({day:eventDay,year:eventYear,crop:harvested,eventKind:"sugarcane_reform",sugarcane_cut:caneCut});
        if(!pendingPlanting||pendingPlanting.day>eventDay)path.push({day:eventDay,year:eventYear,crop:"fallow",fromCrop:lastMainCrop,water,soc,eventKind:"fallow_start",nextDecisionDay:pendingPlanting?.day??null,nextDecisionDecendio:pendingPlanting?.decendio??null,climateYear:historyBlocks[yearIndex][0]});
      }
    }
    if(!crop&&pendingPlanting&&!pendingPlanting.cropId&&pendingPlanting.day<=eventDay){
      const decisionDay=pendingPlanting.day,decisionDecendio=pendingPlanting.decendio;
      const reform=lastMainCrop==="sugarcane";
      const allowed=reform?sugarcaneReformDestinations():eligibleCropDestinations(lastMainCrop,decisionDay);
      if(!allowed.size){pendingPlanting=nextPlantingOpportunity(lastMainCrop,decisionDay+1);}
      else{
        if(!posteriorRows[lastMainCrop])posteriorRows[lastMainCrop]=reform
          ?sampleCropRow(lastMainCrop,rng,allowed,true):sampleCropRow(lastMainCrop,rng);
        const probabilities=cropProbabilities(lastMainCrop,waterFraction,soc,posteriorRows[lastMainCrop],allowed),next=drawProbability(probabilities,rng),transitionProbability=probabilities[next],previous=lastMainCrop,sowOpportunity=nextCropPlantingWindow(next,decisionDay);
        if(!sowOpportunity){pendingPlanting=nextPlantingOpportunity(lastMainCrop,decisionDay+1);}
        else{
          const newStreak=next===previous?consecutivePlantings+1:1;
          path.push({day:decisionDay,year:Math.min(horizon,Math.ceil(decisionDay/daysPerYear)),crop:next,fromCrop:previous,water,soc,transitionProbability,eventKind:"main_transition",plantingDecendio:sowOpportunity.decendio,scheduledPlantingDay:sowOpportunity.day,decisionDecendio,plantingRule:cropCalendarBasisLabel(next),consecutivePlantings:newStreak,repeatYieldMultiplier:repeatedCropYieldMultiplier(next,newStreak),climateYear:historyBlocks[yearIndex][0]});
          if(sowOpportunity.day>decisionDay)path.push({day:decisionDay,year:Math.min(horizon,Math.ceil(decisionDay/daysPerYear)),crop:"fallow",fromCrop:previous,toCrop:next,water,soc,eventKind:"fallow_until_planting",nextPlantingDay:sowOpportunity.day,nextPlantingDecendio:sowOpportunity.decendio,climateYear:historyBlocks[yearIndex][0]});
          pendingPlanting={cropId:next,fromCrop:previous,day:sowOpportunity.day,decendio:sowOpportunity.decendio,consecutivePlantings:newStreak,repeatYieldMultiplier:repeatedCropYieldMultiplier(next,newStreak)};
        }
      }
    }
    if(!crop&&pendingPlanting?.cropId&&pendingPlanting.day<=eventDay){
      const plantingDay=pendingPlanting.day,next=pendingPlanting.cropId,previous=pendingPlanting.fromCrop,elapsedDays=Math.max(0,eventDay-plantingDay),perennial=Boolean(cropLifecycleRule(next));
      crop=next;consecutivePlantings=pendingPlanting.consecutivePlantings;
      if(next==="sugarcane")nextSugarcaneCut=1;
      const firstCycleDuration=Math.max(cycleDays(next),maturationDays(next));mainTimer=Math.max(climatePeriodDays,firstCycleDuration-elapsedDays);maturityRemaining=Math.max(0,maturationDays(next)-elapsedDays);formationTimer=perennial?Math.max(0,daysPerYear-elapsedDays):Infinity;
      path.push({day:plantingDay,year:Math.min(horizon,Math.ceil(plantingDay/daysPerYear)),crop,fromCrop:previous,water,soc,eventKind:"planting",plantingDecendio:pendingPlanting.decendio,consecutivePlantings,repeatYieldMultiplier:pendingPlanting.repeatYieldMultiplier,climateYear:historyBlocks[yearIndex][0]});
      if(perennial)path.push({day:plantingDay,year:Math.min(horizon,Math.ceil(plantingDay/daysPerYear)),crop,water,waterFraction,soc,eventKind:"formation_cost",flowKind:"perennial_formation_cost",flowCrop:crop,cycleDays:Math.min(daysPerYear,maturationDays(crop)),climateYear:historyBlocks[yearIndex][0]});
      pendingPlanting=null;
    }
    if(Number.isFinite(formationTimer)&&maturityRemaining>0&&formationTimer<=0){path.push({day:eventDay,year:eventYear,crop,water,waterFraction,soc,eventKind:"formation_cost",flowKind:"perennial_formation_cost",flowCrop:crop,cycleDays:Math.min(daysPerYear,maturityRemaining),climateYear:historyBlocks[yearIndex][0]});formationTimer+=daysPerYear;}
    if((period+1)%Number(cropCycles.time_basis.environment_periods_per_year)===0){const year=(period+1)/Number(cropCycles.time_basis.environment_periods_per_year);yearStates[year]={crop:crop||"fallow"};environmentPath[year]={water,waterFraction,soc};}
  }
  for(let year=1;year<=horizon;year++){annualPath.push(yearStates[year]||{crop:crop||"fallow"});environmentPath[year]=environmentPath[year]||environmentPath[year-1]||{water,waterFraction,soc};}
  return {path,crop:crop||"fallow",water,waterFraction,soc,annualPath,environmentPath};
}
function quantileSorted(sorted,p){if(!sorted.length)return 0;const i=(sorted.length-1)*p,lo=Math.floor(i),hi=Math.ceil(i);return sorted[lo]+(sorted[hi]-sorted[lo])*(i-lo);}
function quantile(values,p){return quantileSorted([...values].sort((a,b)=>a-b),p);}
function economicYieldMultiplier(water,soc){
  const response=soilHypotheses.economic_yield_response,thresholds=soilHypotheses.soil_carbon.state_thresholds_g_kg;
  const soilClass=soc<Number(thresholds.low_max_exclusive)?"low":soc<Number(thresholds.medium_max_exclusive)?"medium":"high";
  return Number(response.water_multiplier_by_class[water])*Number(response.soil_carbon_multiplier_by_class[soilClass]);
}
function priceAtYear(input,years){const price=Number(input?.price?.brl_per_tonne),trend=Number(input?.price?.trend_annual_fraction||0);return price*Math.pow(1+trend,Math.max(0,years));}

function economicCashflow(step,inputs){
  const cropId=step.flowCrop,input=inputs[cropId],cost=Number(input?.cost_panel?.total_cost_brl_ha_reference_month);
  if(step.flowKind==="main_harvest"){
    const yieldKg=Number(input?.yield_kg_ha_median_2021_2025),price=priceAtYear(input,Number(step.day||0)/Number(cropCycles.time_basis.days_per_year)),multiplier=economicYieldMultiplier(step.water,step.soc)*Number(step.repeatYieldMultiplier??1);
    if(![yieldKg,price,cost].every(Number.isFinite))return NaN;
    return yieldKg/1000*price*multiplier-cost;
  }
  if(step.flowKind==="perennial_formation_cost"){
    if(!Number.isFinite(cost))return NaN;
    const fractions=cropCycles.new_perennial_formation,share=Number(fractions[cropId+"_annual_formation_cost_fraction"]??0.55);
    return -cost*share*Math.min(1,Number(step.cycleDays||365)/Number(cropCycles.time_basis.days_per_year));
  }
  return 0;
}
function scoreTrajectoryVpl(path,inputs,selectedCropIds){
  let vpl=0;
  for(const step of path){
    if(["main_harvest","perennial_formation_cost"].includes(step.flowKind)&&!selectedCropIds.has(step.flowCrop))return null;
  }
  for(const step of path.slice(1)){
    const net=economicCashflow(step,inputs);if(!Number.isFinite(net))return null;
    vpl+=net/Math.pow(1+Number(active.economics.discount_rate.real_annual_rate_approx),Number(step.day||0)/Number(cropCycles.time_basis.days_per_year));
  }
  return Number.isFinite(vpl)?{vpl}:null;
}
function actualRouteEvents(path){
  const initial=path[0]||{},crops=[initial.crop||"fallow"];
  for(const step of path.slice(1)){
    if(step.eventKind==="planting")crops.push(step.crop||"fallow");
  }
  return {crops};
}
function addRotationSample(rotationSamples,result,inputs,selectedCropIds){
  const path=result.path;
  const routeEvents=actualRouteEvents(path),key=JSON.stringify(routeEvents);
  let sample=rotationSamples.get(key);
  if(!sample){sample={frequency:0,values:[],finalSocSum:0,finalWaterFractionSum:0,finalEnvironmentCount:0,finalWaterCounts:{}};rotationSamples.set(key,sample);}
  sample.frequency++;
  sample.finalWaterFractionSum+=result.waterFraction;sample.finalSocSum+=Number(result.soc);sample.finalEnvironmentCount++;
  sample.finalWaterCounts[result.water]=(sample.finalWaterCounts[result.water]||0)+1;
  const scored=scoreTrajectoryVpl(path,inputs,selectedCropIds);if(!scored)return;
  sample.values.push(scored.vpl);
}
function renderCycleAssumptions(){
  const calendar=cropCycles.time_basis.planting_calendar,fallback=cropCycles.rotation_calendar_fallback||{},fallbackNames=(fallback.crop_ids||[]).map(cropLabel).join(", ");
  const cycles=Object.entries(cropCycles.crops).map(([id,item])=>cropLabel(id)+" "+item.cycle_days+"/"+item.maturation_days+" dias ["+item.support+"]").join(" · ");
  byId("cycle-assumptions-detail").textContent="Relógio do modelo: 60 meses, 365 dias/ano; cultura inicial estabelecida e novos plantios aguardam maturação. Ciclos/maturação: "+cycles+". Calendário MAPA SISZARC municipal "+(active.zarc_planting_windows?.source?.current_season||"safra disponível")+", repetido nos cinco anos; riscos "+calendar.risk_levels_included_percent.join("/")+"%, união de grupos de cultivar e classes ZARC. Após cada colheita anual, a decisão Markov espera a próxima oportunidade municipal; pousio continua até a janela de plantio do destino. Regras fixas de efeito por repetição e maturação ficam em data/reference/crop-cycle-assumptions.json.";
  byId("cycle-assumptions-detail").textContent+=" Fallback: "+fallbackNames+" podem usar qualquer decêndio somente sem linha MAPA standalone. É hipótese de disponibilidade para coberturas, não recomendação; calendário oficial sempre prevalece.";
}function renderEconomicInputs(){
  const table=byId("economic-input-table"),head=document.createElement("thead"),header=document.createElement("tr"),body=document.createElement("tbody");
  for(const label of ["Usar","Cultura","Rendimento · kg/ha","Preço-base real · R$/t","Tendência real · %/ano","Custo · R$/ha","Formação perene · % do custo anual","Fontes e regra da hipótese"]){header.append(el("th",label));}
  head.append(header);table.replaceChildren(head,body);
  for(const [cropId,input] of Object.entries(active.economics.crop_inputs)){
    const row=document.createElement("tr"),cost=input.cost_panel,price=input.price,include=document.createElement("input");include.type="checkbox";include.dataset.cropId=cropId;include.checked=Boolean(input.include_in_vpl??input.eligible_for_economic_comparison);include.setAttribute("aria-label","Incluir "+input.label+" no ranking VPL");
    const numberField=(field,value,step,min="0")=>{const control=document.createElement("input");control.type="number";control.min=min;control.step=step;control.value=value===null||value===undefined?"":String(value);control.dataset.cropId=cropId;control.dataset.field=field;control.setAttribute("aria-label",input.label+" · "+field);return control;};
    const includeCell=document.createElement("td");includeCell.append(include);
    const yieldCell=document.createElement("td"),priceCell=document.createElement("td"),trendCell=document.createElement("td"),costCell=document.createElement("td"),formationCell=document.createElement("td");
    yieldCell.append(numberField("yield_kg_ha_median_2021_2025",input.yield_kg_ha_median_2021_2025,"1"));
    priceCell.append(numberField("price_brl_per_tonne",price?.brl_per_tonne,"0.01"));
    trendCell.append(numberField("trend_percent_per_year",Number(price?.trend_annual_fraction||0)*100,"0.1","-100"));
    costCell.append(numberField("cost_brl_ha",cost?.total_cost_brl_ha_reference_month,"0.01"));
    const sourceCell=document.createElement("td"),sourceNotes=[];
    const formationKey=cropId==="sugarcane"?"sugarcane_annual_formation_cost_fraction":null;
    if(formationKey){const formationInput=numberField("formation_cost_percent",Number(cropCycles.new_perennial_formation[formationKey])*100,"1");formationInput.max="100";formationCell.append(formationInput);sourceNotes.push("Formação: "+fmt(100*Number(cropCycles.new_perennial_formation[formationKey]),0)+"% (inicial "+fmt(100*Number(formationFractionBaseline[formationKey]),0)+"%); parcela editável no plantio e em cada ano até maturar, com a última proporcional. Multiplica custo anual proxy, não investimento de implantação observado.");}
    else formationCell.textContent="—";
    if(input.yield_source)sourceNotes.push("Rendimento: "+input.yield_source);
    if(price?.source)sourceNotes.push("Preço: "+price.source);
    if(price?.trend_method)sourceNotes.push("Tendência inicial: "+price.trend_method+" Estimativa bruta "+fmt(100*Number(price.recent_trend_raw_annual_fraction||0),1)+"%/ano, limitada a ±5%/ano.");
    if(price?.history_real_brl_per_tonne?.length){const historyText=price.history_real_brl_per_tonne.map(item=>item.year+": "+brl(item.real_brl_per_tonne,0)+"/t").join(" · ");sourceCell.append(el("small","Histórico real PAM por ano (R$ da moeda-base): "+historyText));}
    if(price?.yahoo_futures_reference)sourceNotes.push("Yahoo Finance futuro "+price.yahoo_futures_reference.symbol+" ("+price.yahoo_futures_reference.quote_date+"): "+brl(price.yahoo_futures_reference.brl_per_tonne)+"/t, mostrado como referência separada, não como preço-base local.");
    if(cost?.source_file){const link=el("a",cost.municipality+"-"+cost.uf+" · "+cost.cost_date);link.href=cost.source_url||"https://www.gov.br/conab/pt-br/atuacao/informacoes-agropecuarias/custos-de-producao/arquivos-custo-de-producao/agricolas";link.target="_blank";link.rel="noreferrer";sourceCell.append(link,el("small",cost.match_level+" · "+cost.sheet));sourceNotes.push(cost.source_note||cost.cost_definition);}
    else if(cost)sourceNotes.push("Valor manual editável; sem painel de fonte atribuído.");
    else sourceNotes.push("Sem painel de custo localizado: defina o valor antes de incluir esta cultura.");
    if(input.assumption_notes?.length)sourceNotes.push(...input.assumption_notes);
    if(input.user_edited_fields?.length){const baseline=input.source_baseline||{};sourceNotes.unshift("VALOR EDITADO em: "+input.user_edited_fields.join(", ")+". Valores-base: rendimento "+(baseline.yield_kg_ha_median_2021_2025??"ausente")+" kg/ha; preço "+(baseline.price_brl_per_tonne??"ausente")+" R$/t; custo "+(baseline.cost_brl_ha??"ausente")+" R$/ha. A fonte listada é a origem do valor-base.");}
    sourceCell.append(el("small",sourceNotes.join(" ")));
    row.append(includeCell,el("td",input.label),yieldCell,priceCell,trendCell,costCell,formationCell,sourceCell);
    if(price)priceCell.title=price.source;
    if(cost)costCell.title=cost.panel_title+" · "+cost.source_file+" · planilha "+cost.sheet;
    yieldCell.title=input.yield_source||"Rendimento editável";
    body.append(row);
  }
}
function weightedQuantile(values,weights,p){
  const ordered=values.map((value,index)=>({value,weight:weights[index]})).filter(item=>item.weight>0).sort((a,b)=>a.value-b.value);
  const total=ordered.reduce((sum,item)=>sum+item.weight,0);if(!total)return 0;
  const target=total*p;let cumulative=0;for(const item of ordered){cumulative+=item.weight;if(cumulative>=target)return item.value;}return ordered.at(-1)?.value||0;
}
function weightedLowerTailMean(values,weights,fraction){
  const ordered=values.map((value,index)=>({value,weight:weights[index]})).filter(item=>item.weight>0).sort((a,b)=>a.value-b.value);
  const target=ordered.reduce((sum,item)=>sum+item.weight,0)*fraction;if(!target)return 0;
  let remaining=target,total=0;for(const item of ordered){const used=Math.min(remaining,item.weight);total+=item.value*used;remaining-=used;if(remaining<=0)break;}return total/target;
}
function applyEconomicInputs(){
  const table=byId("economic-input-table"),entries=active.economics.crop_inputs||{};let invalid=[];
  for(const row of table.querySelectorAll("tbody tr")){
    const checkbox=row.querySelector('input[type="checkbox"]'),cropId=checkbox?.dataset.cropId;if(!cropId||!entries[cropId])continue;
    const values={};for(const control of row.querySelectorAll("input[type=number]"))values[control.dataset.field]=control.value.trim()===""?null:Number(control.value);
    const entry=entries[cropId],priceValue=values.price_brl_per_tonne,costValue=values.cost_brl_ha,yieldValue=values.yield_kg_ha_median_2021_2025;
    if(!entry.source_baseline)entry.source_baseline={yield_kg_ha_median_2021_2025:entry.yield_kg_ha_median_2021_2025,price_brl_per_tonne:entry.price?.brl_per_tonne??null,trend_percent_per_year:Number(entry.price?.trend_annual_fraction||0)*100,cost_brl_ha:entry.cost_panel?.total_cost_brl_ha_reference_month??null};
    const baseline=entry.source_baseline,edited=[];
    if(yieldValue!==baseline.yield_kg_ha_median_2021_2025)edited.push("rendimento");
    if(priceValue!==baseline.price_brl_per_tonne)edited.push("preço");
    if(values.trend_percent_per_year!==baseline.trend_percent_per_year)edited.push("tendência de preço");
    if(costValue!==baseline.cost_brl_ha)edited.push("custo");
    const formationKey=cropId==="sugarcane"?"sugarcane_annual_formation_cost_fraction":null;
    if(formationKey&&Number.isFinite(values.formation_cost_percent)){
      cropCycles.new_perennial_formation[formationKey]=clamp(values.formation_cost_percent/100,0,1);
      if(cropCycles.new_perennial_formation[formationKey]!==formationFractionBaseline[formationKey])edited.push("custo de formação");
    }
    entry.user_edited_fields=edited;
    entry.yield_kg_ha_median_2021_2025=yieldValue;
    entry.price=entry.price||{};entry.price.brl_per_tonne=priceValue;
    entry.price.trend_annual_fraction=Number(values.trend_percent_per_year||0)/100;
    if(!entry.price.source)entry.price.source="Valor de cenário informado pelo usuário; sem preço-base observado.";
    entry.cost_panel=entry.cost_panel||{};entry.cost_panel.total_cost_brl_ha_reference_month=costValue;
    if(!entry.cost_panel.source_file)entry.cost_panel.source_note="Valor de cenário informado pelo usuário; sem painel CONAB atribuído.";
    const complete=[yieldValue,priceValue,costValue].every(value=>Number.isFinite(value)&&value>=0);
    entry.include_in_vpl=checkbox.checked&&complete;entry.eligible_for_economic_comparison=complete;entry.user_edited=true;
    if(checkbox.checked&&!complete)invalid.push(entry.label);
  }
  active.economics.economically_supported_crop_ids=Object.entries(entries).filter(([,entry])=>entry.include_in_vpl).map(([cropId])=>cropId);
  renderCycleAssumptions();
  byId("economic-edit-status").textContent=invalid.length?"Preencha rendimento, preço e custo para incluir: "+invalid.join(", ")+". Recalculando a prévia.":"Premissas aplicadas; recalculando a prévia de 1.000 trajetórias. Use Refinar para acumular mais amostras.";
  startSimulation(currentSeed());
}
function renderEconomicOptimization(start,rotationSamples){
  const states=cropStates(),inputs=active.economics.crop_inputs||{},selected=states.filter(crop=>Boolean(inputs[crop.id]?.include_in_vpl??inputs[crop.id]?.eligible_for_economic_comparison)),rReal=Number(active.economics.discount_rate.real_annual_rate_approx);
  const overallFinalSocMean=latestRun.socValues.length?latestRun.socValues.reduce((sum,value)=>sum+Number(value),0)/latestRun.socValues.length:Number(active.soil.organic_carbon_top_0_30_g_kg),overallWaterMultiplier=waterMultiplierMean(latestRun.waterCounts);
  const yieldHypothesis=soilHypotheses.economic_yield_response,waterText=["water_low","water_medium","water_high"].map(id=>fmt(yieldHypothesis.water_multiplier_by_class[id],2)).join("/");
  const soilText=["low","medium","high"].map(id=>fmt(yieldHypothesis.soil_carbon_multiplier_by_class[id],2)).join("/");
  byId("economic-method").textContent="Cada colheita gera fluxo na data do evento: rendimento × preço real projetado × resposta ambiental × fator fixo de repetição definido no JSON de ciclos − custo. O VPL desconta cada fluxo pela data ("+pct(rReal)+" real ao ano), em R$ de "+active.economics.reference_currency_month.slice(0,4)+"/"+active.economics.reference_currency_month.slice(4)+". Cultura inicial começa estabelecida; nova cultura só gera receita após maturação e calendário. Água multiplica rendimento por "+waterText+" e carbono por "+soilText+". Os padrões de rendimento, preço e custo vêm do JSON econômico; Yahoo fica como referência separada. A nota total combina o score econômico (P95 e, se selecionado, CVaR5 como medida de resiliência) com solo e água finais. A frequência Monte Carlo é exibida como suporte, mas não pontua nem altera a nota.";
  const excluded=states.filter(crop=>!selected.includes(crop)).map(crop=>crop.name);
  byId("economic-coverage-note").textContent="O grafo mantém os "+states.length+" estados. "+selected.length+" culturas estão marcadas para comparação econômica; outras ficam fora do VPL até preencher/ativar premissas, e só são destinos Markov se houver janela MAPA standalone ou hipótese explicitamente marcada para cobertura sem dado. Coberturas sem colheita comercial começam com receita zero e custo proxy editável."+(excluded.length?" Fora do ranking: "+excluded.join(", ")+".":"");
  renderEconomicInputs();
  const routeResults=[];
  for(const [key,sample] of rotationSamples.entries()){
    const routeEvents=JSON.parse(key),values=sample.values||[],n=values.length,routeCrops=routeEvents.crops||[];
    if(!n||!sample.frequency||!selected.some(item=>item.id===start)||routeCrops.some(crop=>crop!=="fallow"&&!selected.some(item=>item.id===crop)))continue;
    const sorted=[...values].sort((a,b)=>a-b),tail=sorted.slice(0,Math.max(1,Math.ceil(sorted.length*.05))),worst=tail.reduce((sum,value)=>sum+value,0)/tail.length;
    const finalEnvironmentCount=Number(sample.finalEnvironmentCount||0),finalWaterCounts=sample.finalWaterCounts||{},finalSocMean=finalEnvironmentCount?Number(sample.finalSocSum)/finalEnvironmentCount:overallFinalSocMean;
    routeResults.push({key,routeEvents,median:quantileSorted(sorted,.5),p95:quantileSorted(sorted,.95),loss:values.filter(value=>value<0).length/values.length,cvar5:worst,count:values.length,tailCount:Math.max(1,Math.ceil(values.length*.05)),frequency:sample.frequency,finalEnvironmentCount,finalSocMean,finalWaterFractionMean:sample.finalWaterFractionSum/finalEnvironmentCount,finalWaterCounts,finalWaterSummary:waterDistributionSummary(finalWaterCounts,finalEnvironmentCount),finalWaterMultiplier:waterMultiplierMean(finalWaterCounts)});
  }
  latestRun.routeResults=routeResults;
  const completed=Number(latestRun.completed||0),frequencyTotal=[...rotationSamples.values()].reduce((sum,sample)=>sum+Number(sample.frequency||0),0),allScoredVplCount=[...rotationSamples.values()].reduce((sum,sample)=>sum+(sample.values||[]).length,0),overcountedGroups=[...rotationSamples.values()].filter(sample=>(sample.values||[]).length>Number(sample.frequency||0)).length,frequencyMismatch=frequencyTotal!==completed;
  const cropName=id=>id==="fallow"?"Pousio":cropLabel(id),routeSequenceLabel=events=>{
    const crops=(events.crops||[]).map((id,index)=>"Plantação "+(index+1)+" · "+cropName(id)+(index===0?" (já estabelecida)":id===events.crops[index-1]?" (replantio)":""));
    return {main:crops.join(" → ")};
  };
  const eligibleValues=routeResults.flatMap(route=>rotationSamples.get(route.key)?.values||[]),eligibleSorted=[...eligibleValues].sort((a,b)=>a-b),referenceTail=eligibleSorted.slice(0,Math.max(1,Math.ceil(eligibleSorted.length*.05))),referenceCvar5=referenceTail.length?referenceTail.reduce((sum,value)=>sum+value,0)/referenceTail.length:0,referenceP95=quantileSorted(eligibleSorted,.95);
  const columns=["Pos.","Sequência de plantios realmente ocorridos","Trajetórias / VPL","Ambiente final · solo e água","Mediana do VPL","P(VPL<0)","CVaR5 · resiliência","P95 · retorno alto","Nota total · 0–10"];
  const table=byId("rotation-path-ranking"),slider=byId("ranking-return-weight"),environmentSlider=byId("ranking-environment-weight"),tablePageInfo=byId("rotation-ranking-page-info"),previous=byId("rotation-ranking-previous"),next=byId("rotation-ranking-next");
  const renderRanking=()=>{
    const returnWeight=Number(slider.value)/100,resilienceWeight=1-returnWeight,environmentWeight=clamp(Number(environmentSlider.value)/100,0,Number(rankingEnvironmentSettings.maximum_weight)),economicWeight=1-environmentWeight,soilShare=Number(rankingEnvironmentSettings.soil_share),waterShare=Number(rankingEnvironmentSettings.water_share),scoreScale=Math.max(Math.abs(referenceCvar5),Math.abs(referenceP95),Number(rankingScoreSettings.minimum_scale_brl_per_ha)),referenceSoilScore=soilScoreOnTen(overallFinalSocMean),referenceWaterScore=waterScoreOnTen(overallWaterMultiplier);
    byId("ranking-return-weight-value").textContent=fmt(100*returnWeight,0)+"% P95 · "+fmt(100*resilienceWeight,0)+"% CVaR5";
    byId("ranking-environment-weight-value").textContent=fmt(100*environmentWeight,0)+"% ambiente · "+fmt(100*economicWeight,0)+"% economia";
    byId("ranking-component-summary").textContent=fmt(100*economicWeight,1)+"% economia ("+fmt(100*economicWeight*returnWeight,1)+"% P95 · "+fmt(100*economicWeight*resilienceWeight,1)+"% CVaR5) · "+fmt(100*environmentWeight*soilShare,1)+"% solo · "+fmt(100*environmentWeight*waterShare,1)+"% água. A frequência Monte Carlo é informativa e não altera a nota.";
    byId("ranking-score-reference").textContent="Escala econômica comum: "+eligibleValues.length.toLocaleString("en-US")+" VPLs · CVaR5 "+brl(referenceCvar5)+"/ha · P95 "+brl(referenceP95)+"/ha. Referência ambiental da simulação: solo médio "+fmt(overallFinalSocMean,1)+" g/kg ("+fmt(referenceSoilScore,1)+"/10) · água final "+waterDistributionSummary(latestRun.waterCounts,latestRun.completed)+" ("+fmt(referenceWaterScore,1)+"/10 ambiental combinado). A nota de cada rotação usa diretamente os resultados dela; contagem de trajetórias e VPLs é mostrada para contextualizar a incerteza, sem ajustar o score.";
    for(const route of routeResults){route.preferenceScore=resilienceWeight*route.cvar5+returnWeight*route.p95;route.preferenceScore10=scoreOnTen(route.preferenceScore,scoreScale);route.soilScore10=soilScoreOnTen(route.finalSocMean);route.waterScore10=waterScoreOnTen(route.finalWaterMultiplier);route.environmentScore=soilShare*route.soilScore10+waterShare*route.waterScore10;route.combinedScore10=economicWeight*route.preferenceScore10+environmentWeight*route.environmentScore;}
    routeResults.sort((a,b)=>b.combinedScore10-a.combinedScore10||b.median-a.median||a.key.localeCompare(b.key));
    const pageCount=Math.max(1,Math.ceil(routeResults.length/rankingPageSize));rotationRankingPage=clamp(rotationRankingPage,0,pageCount-1);
    const head=document.createElement("thead"),header=document.createElement("tr"),body=document.createElement("tbody");for(const label of columns)header.append(el("th",label));head.append(header);table.replaceChildren(head,body);
    const startIndex=rotationRankingPage*rankingPageSize,visibleRows=routeResults.slice(startIndex,startIndex+rankingPageSize);
    if(!routeResults.length){const row=document.createElement("tr"),cell=el("td","Nenhuma rotação com premissas econômicas completas apareceu nesta amostra.");cell.colSpan=columns.length;row.append(cell);body.append(row);}
    visibleRows.forEach((route,index)=>{
      const row=document.createElement("tr");if(startIndex+index===0)row.className="winner-row";
      const sequence=routeSequenceLabel(route.routeEvents),routeCell=el("td",undefined,"route-timeline");routeCell.append(el("strong",sequence.main));
      if(route.count<100)routeCell.append(el("small","Amostra rara: interpretação econômica incerta.","small-muted"));
      const support=el("td",undefined);support.append(el("span",route.frequency.toLocaleString("en-US")+" / "+completed.toLocaleString("en-US")+" · "+pct(route.frequency/Math.max(1,completed))));support.append(el("small","VPLs completos: "+route.count.toLocaleString("en-US")+" · cauda CVaR5: "+route.tailCount.toLocaleString("en-US"),"small-muted"));
      const environmentCell=el("td",undefined);environmentCell.append(el("span",fmt(route.finalSocMean,1)+" g/kg solo"));environmentCell.append(el("small","Água: "+route.finalWaterSummary+" · notas solo "+fmt(route.soilScore10,1)+"/10, água "+fmt(route.waterScore10,1)+"/10","small-muted"));
      const scoreCell=el("td",undefined);scoreCell.append(el("strong",fmt(route.combinedScore10,1)+"/10"));scoreCell.append(el("small","Economia "+fmt(route.preferenceScore10,1)+"/10 · ambiente "+fmt(route.environmentScore,1)+"/10","small-muted"));
      row.append(el("td",String(startIndex+index+1)),routeCell,support,environmentCell,el("td",brl(route.median)+"/ha"),el("td",pct(route.loss)),el("td",brl(route.cvar5)+"/ha"),el("td",brl(route.p95)+"/ha"),scoreCell);body.append(row);
    });
    tablePageInfo.textContent=routeResults.length.toLocaleString("en-US")+" sequências · página "+(routeResults.length?rotationRankingPage+1:0)+" de "+(routeResults.length?pageCount:0)+" · "+rankingPageSize+" por página";
    previous.disabled=rotationRankingPage<=0;next.disabled=rotationRankingPage>=pageCount-1;
    previous.onclick=()=>{if(rotationRankingPage<=0)return;rotationRankingPage--;renderRanking();};
    next.onclick=()=>{if(rotationRankingPage>=pageCount-1)return;rotationRankingPage++;renderRanking();};
    if(!routeResults.length){const audit=byId("ranking-audit");audit.replaceChildren();const card=el("div",undefined,"audit-card");card.append(el("strong",frequencyMismatch||overcountedGroups?"Verificar contagens":"Simulação contabilizada"),el("span",completed.toLocaleString("en-US")+" trajetórias · "+frequencyTotal.toLocaleString("en-US")+" ocorrências agrupadas"),el("small",allScoredVplCount.toLocaleString("en-US")+" VPLs calculados; nenhuma sequência passou os filtros econômicos do ranking."));audit.append(card);byId("vpl-status").textContent="Nenhuma rotação com premissas econômicas completas apareceu. Marque culturas com valores numéricos e aplique as premissas.";return;}
    const best=routeResults[0],sequenceBest=routeSequenceLabel(best.routeEvents);
    const rankedFrequency=routeResults.reduce((sum,route)=>sum+route.frequency,0),rankedVplCount=routeResults.reduce((sum,route)=>sum+route.count,0),missingVpl=Math.max(0,rankedFrequency-rankedVplCount),excludedVpl=Math.max(0,allScoredVplCount-rankedVplCount),unrankedFrequency=Math.max(0,completed-rankedFrequency),overcountedRoutes=routeResults.filter(route=>route.count>route.frequency).length;
    const audit=byId("ranking-audit");audit.replaceChildren();
    const auditCard=(title,value,detail)=>{const card=el("div",undefined,"audit-card");card.append(el("strong",title),el("span",value),el("small",detail));audit.append(card);};
    auditCard(frequencyMismatch||overcountedGroups?"Integridade · verificar":"Integridade · confere",completed.toLocaleString("en-US")+" trajetórias acumuladas · teto "+maxTrajectories.toLocaleString("en-US"), "Frequências nas sequências: "+frequencyTotal.toLocaleString("en-US")+(frequencyMismatch?" (diferença de "+Math.abs(frequencyTotal-completed).toLocaleString("en-US")+")":" (soma confere)")+(overcountedGroups?" · "+overcountedGroups+" grupo(s) com mais VPLs que trajetórias":""));
    auditCard("Cobertura econômica",rankedVplCount.toLocaleString("en-US")+" VPLs usados · "+routeResults.length.toLocaleString("en-US")+" sequências",allScoredVplCount.toLocaleString("en-US")+" VPLs calculados no total; "+missingVpl.toLocaleString("en-US")+" trajetória(s) em rotas listadas sem VPL completo; "+excludedVpl.toLocaleString("en-US")+" VPL(s) fora do ranking por filtros econômicos; "+unrankedFrequency.toLocaleString("en-US")+" trajetórias não comparáveis no ranking.");
    auditCard("Peso da nota",fmt(100*economicWeight,0)+"% economia · "+fmt(100*environmentWeight,0)+"% solo/água","Dentro da economia: "+fmt(100*returnWeight,0)+"% P95 e "+fmt(100*resilienceWeight,0)+"% CVaR5. A frequência é exibida, mas não pontua nem ajusta a nota.");
    if(frequencyMismatch||overcountedGroups||overcountedRoutes){const warning=el("div","Há uma divergência nas contagens que merece inspeção.","audit-card");warning.setAttribute("role","alert");audit.append(warning);}
    byId("vpl-status").textContent="Melhor sequência nesta preferência: "+sequenceBest.main+" · nota total "+fmt(best.combinedScore10,1)+"/10 (economia "+fmt(best.preferenceScore10,1)+" · solo "+fmt(best.soilScore10,1)+" · água "+fmt(best.waterScore10,1)+") · final: solo "+fmt(best.finalSocMean,1)+" g/kg, água "+best.finalWaterSummary+" · mediana "+brl(best.median)+"/ha · CVaR5 "+brl(best.cvar5)+"/ha · P95 "+brl(best.p95)+"/ha · "+best.frequency.toLocaleString("en-US")+" trajetórias ("+best.count.toLocaleString("en-US")+" com VPL)."+(best.count<100?" Amostra rara; resultado pouco estável.":"");
  };
  slider.disabled=!routeResults.length;slider.oninput=()=>{rotationRankingPage=0;renderRanking();};environmentSlider.disabled=!routeResults.length;environmentSlider.oninput=()=>{rotationRankingPage=0;renderRanking();};
  renderRanking();
}
function initialSugarcaneCut(start){
  return start==="sugarcane"?Number(byId("initial-sugarcane-cut").value):1;
}
function createSimulationSession(seed){
  const profile=active,history=Object.entries(profile.water_markov.environment_years).filter(([,block])=>Array.isArray(block)&&block.length===profile.water_markov.periods_per_year),start=byId("initial-crop-select").value;
  const selectedEconomicIds=new Set(cropStates().filter(crop=>Boolean(profile.economics.crop_inputs?.[crop.id]?.include_in_vpl??profile.economics.crop_inputs?.[crop.id]?.eligible_for_economic_comparison)).map(crop=>crop.id));
  return {profile,start,initialSugarcaneCut:initialSugarcaneCut(start),seed,rng:seeded(seed),history,selectedEconomicIds,waterCounts:{},socValues:[],rotationSamples:new Map(),environmentCountsByYear:Array.from({length:horizon+1},environmentCountFrame),nodeCountsByYear:Array.from({length:horizon+1},()=>({})),edgeCountsByYear:Array.from({length:horizon+1},()=>({})),completed:0,previousLeaderKey:null,stableLeaderCheckpoints:0,running:false};
}
function nextRefinementTarget(completed){
  return (monteCarloSettings.refinement_targets||[]).map(Number).find(target=>target>completed)||null;
}
function updateRefinementControls(running=false){
  const state=simulationSession,ready=Boolean(state?.history?.length),refine=byId("refine-simulation"),complete=byId("complete-simulation"),next=ready?nextRefinementTarget(state.completed):null;
  refine.disabled=running||!ready||!next;refine.textContent=next?"Refinar para "+fmt(next,0):"Amostra máxima concluída";
  complete.disabled=running||!ready||state.completed>=maxTrajectories;
}
function updateRefinementCheckpoint(state){
  const best=state.routeResults?.[0]||null,minLeaderSamples=Number(monteCarloSettings.minimum_leader_vpl_samples),stableStages=Number(monteCarloSettings.stable_leader_checkpoints);
  if(best&&state.previousLeaderKey===best.key&&best.count>=minLeaderSamples)state.stableLeaderCheckpoints++;
  else state.stableLeaderCheckpoints=0;
  state.previousLeaderKey=best?.key||null;
  const next=nextRefinementTarget(state.completed),lead=best?best.routeEvents.crops.map(cropLabel).join(" →"):"sem rota com VPL completo";
  if(state.stableLeaderCheckpoints>=stableStages&&best&&best.count>=minLeaderSamples){
    byId("simulation-refinement-status").textContent="A mesma rota liderou em "+(state.stableLeaderCheckpoints+1)+" etapas e tem "+best.count.toLocaleString("en-US")+" VPLs completos. É um sinal de estabilidade do ranking, não prova de convergência; você pode parar ou continuar até "+fmt(maxTrajectories,0)+".";
  }else if(next){
    byId("simulation-refinement-status").textContent="Etapa "+state.completed.toLocaleString("en-US")+" concluída. Líder: "+lead+" · "+(best?.count||0).toLocaleString("en-US")+" VPLs completos. Próxima etapa: "+fmt(next,0)+".";
  }else{
    byId("simulation-refinement-status").textContent="Amostra máxima de "+fmt(maxTrajectories,0)+" concluída. Líder: "+lead+" · "+(best?.count||0).toLocaleString("en-US")+" VPLs completos.";
  }
}
async function renderSimulation(seed,target=Number(monteCarloSettings.initial_preview_trajectories),reset=true){
  const runId=++simulationRunId,status=byId("run-status"),progress=byId("simulation-progress"),progressText=byId("simulation-progress-text"),start=byId("initial-crop-select").value;
  const current=simulationSession;
  if(reset||!current||current.profile!==active||current.start!==start||current.seed!==seed||current.initialSugarcaneCut!==initialSugarcaneCut(start))simulationSession=createSimulationSession(seed);
  const state=simulationSession;
  if(!state.history.length){status.textContent="Não há blocos climáticos completos para simular.";progressText.textContent="Sem clima completo";updateRefinementControls(false);return;}
  if(state.completed===0)renderEnvironmentalDistributionCharts(state.environmentCountsByYear,0);
  const targetLimit=clamp(Math.floor(Number(target)||Number(monteCarloSettings.initial_preview_trajectories)),state.completed,maxTrajectories);
  if(state.completed>=targetLimit){updateRefinementControls(false);return;}
  state.running=true;latestRun=state;byId("ranking-return-weight").disabled=true;byId("ranking-environment-weight").disabled=true;updateRefinementControls(true);
  progress.max=maxTrajectories;progress.value=state.completed;
  status.textContent="Monte Carlo · continuando a amostra com semente "+seed+".";progressText.textContent=state.completed.toLocaleString("en-US")+" / "+maxTrajectories.toLocaleString("en-US")+" trajetórias acumuladas";
  const progressEvery=Math.max(1,Number(monteCarloSettings.progress_interval)),graphRefreshEvery=Math.max(progressEvery,Number(monteCarloSettings.graph_refresh_interval)),yieldToBrowser=()=>new Promise(resolve=>requestAnimationFrame(()=>resolve()));
  while(state.completed<targetLimit){
    let processed=0;
    while(processed<progressEvery&&state.completed<targetLimit){
      const result=sampleTrajectory(state.start,state.rng,state.history,state.initialSugarcaneCut);
      state.waterCounts[result.water]=(state.waterCounts[result.water]||0)+1;state.socValues.push(result.soc);
      for(let year=0;year<result.environmentPath.length;year++){
        const environment=result.environmentPath[year],frame=state.environmentCountsByYear[year];
        if(!environment||!frame)continue;
        frame.water[environment.water]=(frame.water[environment.water]||0)+1;
        const soilId=soilStateId(environment.soc);frame.soil[soilId]=(frame.soil[soilId]||0)+1;
      }
      state.nodeCountsByYear[0][state.start]=(state.nodeCountsByYear[0][state.start]||0)+1;
      for(let year=0;year<result.annualPath.length;year++){
        const annual=result.annualPath[year],yearNumber=year+1;
        if(annual.crop!=="fallow")state.nodeCountsByYear[yearNumber][annual.crop]=(state.nodeCountsByYear[yearNumber][annual.crop]||0)+1;
      }
      for(const step of result.path){
        if(step.eventKind==="main_transition"){
          const year=Math.max(1,Math.min(horizon,Number(step.year)||1)),key=step.fromCrop+"|"+step.crop;
          state.edgeCountsByYear[year][key]=(state.edgeCountsByYear[year][key]||0)+1;
        }
      }
      addRotationSample(state.rotationSamples,result,state.profile.economics.crop_inputs||{},state.selectedEconomicIds);
      state.completed++;processed++;
    }
    latestRun=state;progress.value=state.completed;
    progressText.textContent=state.completed.toLocaleString("en-US")+" / "+maxTrajectories.toLocaleString("en-US")+" trajetórias acumuladas";
    status.textContent="Monte Carlo em execução · "+fmt(100*state.completed/maxTrajectories,1)+"% do teto · "+state.completed.toLocaleString("en-US")+" trajetórias";
    if(state.completed%graphRefreshEvery===0&&state.completed<targetLimit){renderCropGraph(byId("matrix-water-select").value,Number(byId("matrix-carbon-input").value),state.nodeCountsByYear,state.edgeCountsByYear,state.completed);renderEnvironmentalDistributionCharts(state.environmentCountsByYear,state.completed);}
    await yieldToBrowser();if(runId!==simulationRunId){state.running=false;return;}
  }
  status.textContent="Amostra de "+state.completed.toLocaleString("en-US")+" concluída; atualizando cadeia e VPL.";
  await yieldToBrowser();if(runId!==simulationRunId){state.running=false;return;}
  state.running=false;state.socMedian=quantile(state.socValues,0.5);
  state.finalWater=[...Object.entries(state.waterCounts)].sort((a,b)=>b[1]-a[1])[0]?.[0]||"water_medium";
  latestRun=state;byId("matrix-water-select").value=state.finalWater;byId("matrix-carbon-input").value=state.socMedian.toFixed(1);renderEnvironmentalDistributionCharts(state.environmentCountsByYear,state.completed);
  renderCropMatrix();
  renderEconomicOptimization(state.start,state.rotationSamples);
  const rankSlider=byId("ranking-return-weight"),environmentSlider=byId("ranking-environment-weight");rankSlider.disabled=!state.routeResults?.length;environmentSlider.disabled=!state.routeResults?.length;
  updateRefinementCheckpoint(state);updateRefinementControls(false);
  if(state.completed>=maxTrajectories){
    progress.value=maxTrajectories;progressText.textContent=maxTrajectories.toLocaleString("en-US")+" trajetórias · amostra máxima";
    status.textContent="Monte Carlo concluído · "+maxTrajectories.toLocaleString("en-US")+" trajetórias · "+horizonMonths+" meses.";
  }else{
    progressText.textContent=state.completed.toLocaleString("en-US")+" / "+maxTrajectories.toLocaleString("en-US")+" trajetórias · prévia disponível";
    status.textContent="Prévia Monte Carlo pronta · "+state.completed.toLocaleString("en-US")+" trajetórias acumuladas. Refine se precisar de mais suporte.";
  }
}
function startSimulation(seed,target=Number(monteCarloSettings.initial_preview_trajectories),reset=true){
  const expectedRunId=simulationRunId+1;rotationRankingPage=0;
  void renderSimulation(seed,target,reset).catch(error=>{
    if(expectedRunId!==simulationRunId)return;
    const state=simulationSession;if(state)state.running=false;
    updateRefinementControls(false);
    byId("run-status").textContent="Monte Carlo interrompido: "+(error?.message||String(error));
    byId("simulation-progress-text").textContent="Falha após "+Number(state?.completed||0).toLocaleString("en-US")+" trajetórias";
    console.error("Falha no Monte Carlo",error);
  });
}
function renderProfile(){
  const profileRenderId=++simulationRunId;active=profiles[byId("case-select").value];latestRun=null;
  byId("soil-baseline").textContent=fmt(active.soil.organic_carbon_top_0_30_g_kg,1)+" g/kg";
  byId("soil-scope").textContent="SoilGrids · "+active.soil.scope+" · "+active.soil.sample_point_basis;
  byId("crop-period").textContent=active.crop_markov.annual_observation_count+" anos municipais · "+active.crop_markov.period[0]+"–"+active.crop_markov.period[1]+" · "+active.crop_markov.adjacent_year_transition_count+" pares consecutivos · top "+active.crop_markov.top_crop_limit+" por área · "+active.crop_markov.states.length+" estados de cultura.";
  byId("crop-data-note").textContent="Uma cultura principal por talhão. Soja, milho e cana podem iniciar; as demais são destinos quando há janela municipal MAPA ou uma hipótese explicitamente marcada para cobertura sem dado. A cadeia considera a distribuição PAM do top 5 por área e forma transições marginais entre anos com independência assumida; a PAM não liga culturas ao mesmo talhão. A série rank 1 aparece como diagnóstico separado. Datas são decêndios das tábuas anual 2026/2027 e perene vigente repetidas nos cinco anos; classes de solo e grupos de cultivar são agregados."+beanCalendarAuditNote();
  const lifecycleNote=byId("crop-lifecycle-note");
  lifecycleNote.replaceChildren();
  lifecycleNote.append(el("strong","Perenes e maturação."),document.createTextNode(" A matriz regional mostra a permanência da cana nas socas. No Monte Carlo, o próximo corte é informado para um canavial existente. O quinto corte abre a rotação com culturas anuais elegíveis, usando a PAM regional como prior. Rendimento e custo usam o mesmo benchmark em todos os cortes; o custo de remoção da soqueira não está separado. Novos plantios passam por maturação e custos de formação."));
  const rankOnePairs=active.crop_markov.transitions.reduce((sum,row)=>sum+Number(row.count||0),0);
  byId("crop-source-detail").textContent="Fonte: "+active.crop_markov.source.publisher+" · "+active.crop_markov.source.survey+", tabela "+active.crop_markov.source.table+" · município IBGE "+active.crop_markov.source.municipality_ibge_code+" · área colhida em hectares. Para cada ano, o top "+active.crop_markov.top_crop_limit+" entre as culturas mapeadas é normalizado pela área do próprio top 5. Os "+active.crop_markov.area_weighted_transition_pair_count+" pares anuais geram massa esperada pela multiplicação das participações t × t+1; "+rankOnePairs+" pares rank 1 das arestas elegíveis são informados separadamente, sem dupla contagem na probabilidade.";
  byId("mapbiomas-note").textContent="O relatório de pesquisa cita sequências e seis tabelas MapBiomas, mas esses arquivos não estão neste checkout. Os assets oficiais de uso agrícola e carbono do solo são publicados pelo MapBiomas; não foram usados para preencher contagens ausentes nesta página. Assim, a cadeia fica baseada na PAM e identifica sua escala municipal.";
  byId("water-period").textContent="Estados hídricos por quinzena · treino "+active.water_markov.years[0]+"–"+active.water_markov.years[1]+" · balanço de referência Kc=1.";
  byId("water-provenance").textContent=active.water_markov.provenance+" Cada bloco climático é sorteado para um ano do horizonte; a classe de água evolui a cada quinzena e condiciona as transições ao fim dos ciclos.";
  renderCycleAssumptions();
  const selectedPrice=active.economics.crop_inputs.soybean?.price;
  byId("price-projection-detail").textContent="Preço/VPL: preço-base PAM = mediana dos preços anuais reais de 2017–2025, todos em R$ constantes de "+active.economics.reference_currency_month.slice(0,4)+"/"+active.economics.reference_currency_month.slice(4)+". A tendência parte da CAGR entre as medianas dos três primeiros e dos três últimos anos e é limitada a ±5% ao ano; pode ser editada cultura a cultura. Cada receita/custo é descontado pela data exata do evento; taxa real aproximada atual: "+pct(active.economics.discount_rate.real_annual_rate_approx)+". Yahoo CBOT de soja/milho aparece como referência separada, não substitui a PAM."+(selectedPrice?.history_real_brl_per_tonne?.length?" Série usada para soja neste perfil: "+selectedPrice.history_real_brl_per_tonne.map(item=>item.year+" "+brl(item.real_brl_per_tonne,0)+"/t").join(" · "):"");
  const cropSelect=byId("initial-crop-select"),previous=cropSelect.value;cropSelect.replaceChildren();
  for(const id of active.crop_markov.initial_crop_ids){const crop=cropStateMap()[id];cropSelect.add(new Option(crop.name,crop.id));}
  cropSelect.value=active.crop_markov.initial_crop_ids.includes(previous)?previous:"soybean";
  byId("technical-sugarcane-cut-field").hidden=cropSelect.value!=="sugarcane";
  const waterSelect=byId("matrix-water-select");waterSelect.replaceChildren();
  for(const state of active.water_markov.states)waterSelect.add(new Option(state.label,state.id));
  waterSelect.value="water_medium";
  const graphYearSelect=byId("graph-year-select");graphYearSelect.replaceChildren();
  for(let year=0;year<=horizon;year++)graphYearSelect.add(new Option(year===0?"0 · estado inicial":""+year+" · ano "+year,String(year)));
  graphYearSelect.add(new Option("Ciclo completo · 5 anos","all"));graphYearSelect.value="all";selectedGraphCropId=cropSelect.value;
  const decendioSelect=byId("matrix-planting-decendio");decendioSelect.replaceChildren();for(let decendio=1;decendio<=36;decendio++)decendioSelect.add(new Option(decendioName(decendio),String(decendio)));decendioSelect.value="1";
  byId("matrix-carbon-input").value=active.soil.organic_carbon_top_0_30_g_kg.toFixed(1);
  simulationSession=null;updateRefinementControls(false);
  renderCropTimeline();renderCropMatrix();renderWaterMatrix();byId("simulation-progress").value=0;byId("simulation-progress-text").textContent="Aguardando simulação";byId("run-status").textContent="Cadeia pronta; o Monte Carlo começará após a página aparecer.";
  byId("run-status").textContent="Perfil pronto. Inicie a análise na experiência principal ou use os controles avançados.";
}

for(const item of cases.cases)byId("case-select").add(new Option(item.municipality+" · "+item.uf,item.profile));
for(let cut=1;cut<=cycleRule("sugarcane").modeled_harvest_cuts;cut++){
  byId("initial-sugarcane-cut").add(new Option(cut+"º corte",String(cut)));
}
renderVplReferences();
byId("case-select").addEventListener("change",renderProfile);
byId("initial-crop-select").addEventListener("change",()=>{
  selectedGraphCropId=byId("initial-crop-select").value;
  byId("technical-sugarcane-cut-field").hidden=selectedGraphCropId!=="sugarcane";
  startSimulation(currentSeed());
});
byId("initial-sugarcane-cut").addEventListener("change",()=>startSimulation(currentSeed()));
byId("matrix-water-select").addEventListener("change",renderCropMatrix);
byId("matrix-carbon-input").addEventListener("input",renderCropMatrix);
byId("matrix-planting-decendio").addEventListener("change",renderCropMatrix);
byId("graph-year-select").addEventListener("change",()=>{renderCropGraph(byId("matrix-water-select").value,Number(byId("matrix-carbon-input").value),latestRun?.nodeCountsByYear||{},latestRun?.edgeCountsByYear||{},latestRun?.completed||0);});
byId("apply-economic-inputs").addEventListener("click",applyEconomicInputs);
byId("simulation-seed").addEventListener("change",()=>startSimulation(currentSeed()));
byId("run-simulation").addEventListener("click",()=>startSimulation(currentSeed()));
byId("refine-simulation").addEventListener("click",()=>{const next=nextRefinementTarget(simulationSession?.completed||0);if(next)startSimulation(currentSeed(),next,false);});
byId("complete-simulation").addEventListener("click",()=>startSimulation(currentSeed(),maxTrajectories,false));
byId("case-select").value=cases.cases[0].profile;
renderProfile();
