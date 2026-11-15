(() => {
  "use strict";
  const $ = id => document.getElementById(id);
  const farmerUI = { screen:"location", city:null, crop:null, target:100000, running:false, runToken:0, startedAt:0 };
  const screenIds = { location:"screen-location", crop:"screen-crop", priority:"screen-priority", simulation:"screen-simulation", result:"screen-result" };
  const stepByScreen = { location:1, crop:2, priority:3, simulation:4, result:4 };
  const farmerCropNames = { soybean:"Soybean", maize_grain:"Corn", sugarcane:"Sugarcane", sorghum_grain:"Sorghum", wheat:"Wheat", dry_bean:"Dry bean", peanut:"Peanut", oat:"Black oat", forage_radish:"Forage radish", brachiaria:"Brachiaria", millet:"Millet", crotalaria:"Crotalaria", mucuna:"Mucuna", fallow:"Fallow" };
  const farmerCropColors = { soybean:"#6c954d", maize_grain:"#d6a83e", sugarcane:"#7a9d50", sorghum_grain:"#b98545", wheat:"#c8a85d", dry_bean:"#9a7151", peanut:"#b78b50", oat:"#90a469", forage_radish:"#7c9a67", brachiaria:"#5f8b58", millet:"#a18b54", crotalaria:"#7d9b4f", mucuna:"#68895d", fallow:"#9a8b75" };
  const icon = name => `<svg aria-hidden="true"><use href="#i-${name}"/></svg>`;

  function cropArtInner(crop) {
    const green="#477a45", dark="#315e39", light="#77a657", soil="#9a7954";
    if (crop === "soybean") return `<path d="M20 105h80v6H20z" fill="#d7c5a3"/><path d="M57 100h6V43h-6z" fill="${dark}"/><path d="M60 57 39 43l-4 5 22 19zm2 14 22-17 4 5-25 22zM59 83 38 70l-4 5 23 17z" fill="${green}"/><path d="M34 37h18v7H38v7H25v-7h9zm49 10h18v8H88v7H75v-8h8zM28 64h18v7H34v7H20v-8h8z" fill="${light}"/><path d="M68 77h8v20h-8zM46 82h8v17h-8z" fill="#c4a849"/><path d="M70 80h3v13h-3zM48 85h3v10h-3z" fill="#e1c967"/>`;
    if (crop === "maize_grain") return `<path d="M20 105h80v6H20z" fill="#d7c5a3"/><path d="M57 101h7V22h-7z" fill="${dark}"/><path d="M57 46 36 29h-8v7l29 24zm7 15 28-22h8v8L64 76zM57 75 33 57h-9v8l33 25z" fill="${green}"/><path d="M66 45h14v25H66z" fill="#d9ad37"/><path d="M69 48h3v3h-3zm6 0h3v3h-3zm-6 6h3v3h-3zm6 6h3v3h-3zm-6 6h3v3h-3z" fill="#f2d365"/><path d="m64 42 16-7v12l-9-2zm0 9-9 19h9l8-19z" fill="${light}"/><path d="M54 21h14v5H54z" fill="#b4944b"/>`;
    if (crop === "sugarcane") return `<path d="M16 105h88v6H16z" fill="#d7c5a3"/><path d="M34 100h6V27h-6zm25 0h6V15h-6zm25 0h6V31h-6z" fill="#78964d"/><path d="M34 49h6v5h-6zm0 22h6v5h-6zm25-32h6v5h-6zm0 25h6v5h-6zm25-12h6v5h-6zm0 24h6v5h-6z" fill="#d0bd67"/><path d="M37 43 20 22h-6v8l20 26zm3 23 22-22h7v8L40 80zm22-35L44 9h-7v8l22 28zm3 30 23-24h8v8L65 76zm22-13 19-22h-7l-12 13z" fill="${green}"/><path d="M59 15 70 2h8L65 22zM34 27l-8-20h7l7 20z" fill="${light}"/>`;
    const color=farmerCropColors[crop]||green;
    return `<path d="M20 105h80v6H20z" fill="#d7c5a3"/><path d="M57 102h7V48h-7z" fill="${dark}"/><path d="M59 66C40 66 31 56 31 39c19 0 28 10 28 27Zm3 12c0-19 9-29 28-29 0 17-9 27-28 29Z" fill="${color}"/><path d="M58 91C43 91 35 83 35 70c15 0 23 8 23 21Z" fill="${light}"/>`;
  }
  function cropArtwork(crop) { return `<svg viewBox="0 0 120 120" shape-rendering="crispEdges" aria-hidden="true">${cropArtInner(crop)}</svg>`; }
  function farmerCropName(id) { return farmerCropNames[id] || cropLabel(id) || id; }
  function selectedCityData() { return cases.cases.find(item => item.profile === farmerUI.city) || null; }

  function showFarmerScreen(name) {
    farmerUI.screen=name;
    for (const [key,id] of Object.entries(screenIds)) $(id).hidden=key!==name;
    $("farmer-error").hidden=true;
    const current=stepByScreen[name];
    document.querySelectorAll(".journey-step").forEach(step=>{
      const number=Number(step.dataset.step);
      step.classList.toggle("is-active",number===current);
      step.classList.toggle("is-done",number<current);
      step.querySelector(".journey-number").innerHTML=number<current?icon("check"):String(number);
    });
    window.scrollTo({top:0,behavior:matchMedia("(prefers-reduced-motion: reduce)").matches?"auto":"smooth"});
  }

  function selectCity(profile) {
    if (farmerUI.running) return;
    farmerUI.city=profile;
    const city=selectedCityData();
    document.querySelectorAll("[data-profile]").forEach(node=>{
      const selected=node.dataset.profile===profile;
      node.classList.toggle("is-selected",selected);
      node.setAttribute("aria-pressed",String(selected));
    });
    $("city-selection-note").innerHTML=`<strong style="color:var(--fs-green)">${city.municipality}, ${city.uf}</strong><br>Climate, soil, and cropping history ready for analysis.`;
    $("location-next").disabled=false;
    document.querySelectorAll("[data-selected-city]").forEach(node=>node.textContent=`${city.municipality} · ${city.uf}`);
    if ($("case-select").value!==profile) { $("case-select").value=profile; renderProfile(); }
  }

  function selectCrop(crop) {
    farmerUI.crop=crop;
    $("farmer-sugarcane-cut-field").hidden=crop!=="sugarcane";
    document.querySelectorAll(".crop-choice").forEach(node=>{
      const selected=node.dataset.crop===crop;
      node.classList.toggle("is-selected",selected);
      node.setAttribute("aria-pressed",String(selected));
    });
    $("crop-next").disabled=false;
    document.querySelectorAll("[data-selected-crop]").forEach(node=>node.textContent=farmerCropName(crop));
  }

  function updatePriority() {
    const environment=Number($("farmer-priority").value),finance=100-environment;
    $("priority-value-copy").textContent=`${finance}% financial return · ${environment}% soil and water · excluding fixed sample support`;
    $("priority-value-title").textContent=environment===0?"Fully focused on returns":environment<20?"Stronger focus on returns":environment===20?"Balanced, with a focus on returns":environment<40?"Balanced, with a focus on soil and water":environment<50?"Stronger focus on soil and water":"Soil and water come first";
  }

  function renderGrowth(progress) {
    const crop=farmerUI.crop||"soybean",stage=progress<.16?0:progress<.42?1:progress<.74?2:3;
    const labels=["Preparing the soil","Planting the first seeds","The crop is growing","Ready for harvest"];
    $("growth-stage-label").textContent=labels[stage];
    let plants="";
    if(stage>0) {
      const size=[0,58,91,125][stage],y=249-size;
      for(let index=0;index<7;index++) {
        const x=126+index*94,scale=index%2?.92:1;
        plants+=`<svg x="${x}" y="${y+(1-scale)*size}" width="${size}" height="${size}" viewBox="0 0 120 120" shape-rendering="crispEdges" opacity="${stage===1?.8:1}">${cropArtInner(crop)}</svg>`;
      }
    } else {
      for(let index=0;index<7;index++) plants+=`<rect x="${161+index*94}" y="245" width="7" height="4" rx="2" fill="#705c43"/>`;
    }
    $("growth-svg").innerHTML=`<defs><linearGradient id="growth-sky" x1="0" y1="0" x2="0" y2="1"><stop stop-color="#eaf3ee"/><stop offset="1" stop-color="#f7f7e9"/></linearGradient><linearGradient id="growth-ground" x1="0" y1="0" x2="0" y2="1"><stop stop-color="#c7b184"/><stop offset="1" stop-color="#a78d62"/></linearGradient></defs><rect width="850" height="330" fill="url(#growth-sky)"/><circle cx="710" cy="67" r="34" fill="#efd895" opacity=".75"/><g fill="#fff" opacity=".72"><path d="M100 77h104a22 22 0 0 0-20-30 30 30 0 0 0-54-9 24 24 0 0 0-30 39Z"/><path d="M490 100h84a18 18 0 0 0-16-25 25 25 0 0 0-45-8 20 20 0 0 0-23 33Z"/></g><path d="M0 213q120-35 240-5t230-4q190-39 380 2v124H0Z" fill="#91ac78"/><path d="M0 245q205-26 425-5t425-4v94H0Z" fill="url(#growth-ground)"/><g fill="none" stroke="#8f7854" stroke-width="3" opacity=".55"><path d="M0 282q210-24 425-7t425-4M0 313q210-24 425-7t425-4"/></g><path d="M0 244q205-25 425-5t425-4" fill="none" stroke="#e0cfa8" stroke-width="3"/>${plants}`;
  }

  function updateSimulationProgress(completed) {
    const target=farmerUI.target,fraction=Math.min(1,completed/Math.max(1,target)),percent=Math.floor(fraction*100);
    $("farmer-progress-bar").style.width=`${fraction*100}%`;
    $("farmer-progress").setAttribute("aria-valuenow",String(percent));
    $("farmer-progress-count").textContent=`${completed.toLocaleString("en-US")} of ${target.toLocaleString("en-US")} scenarios`;
    $("farmer-progress-percent").textContent=`${percent}%`;
    $("simulation-friendly-status").textContent=fraction<.25?"Analyzing your region's climate and conditions.":fraction<.55?"Tracking water and soil health through each crop cycle.":fraction<.85?"Comparing crops and rotation possibilities.":"Choosing the sequence that best matches your priorities.";
    if (!renderGrowth.lastBucket || Math.abs(renderGrowth.lastBucket-fraction)>.02 || fraction===1) { renderGrowth(fraction); renderGrowth.lastBucket=fraction; }
  }

  function soilFriendly(value) {
    const limits=soilHypotheses.soil_carbon.state_thresholds_g_kg;
    if(value<Number(limits.low_max_exclusive)) return "Needs care";
    if(value<Number(limits.medium_max_exclusive)) return "Fair";
    return "Good";
  }
  function routeLabel(route) { return (route.routeEvents.crops||[]).map(farmerCropName).join(" → "); }
  function chartMoney(value) { return new Intl.NumberFormat("en-US",{style:"currency",currency:"BRL",notation:"compact",maximumFractionDigits:1}).format(Number(value)); }

  function renderReturnChart(best,values) {
    const svg=$("return-distribution-chart"),width=760,height=225,left=46,right=33,top=25,bottom=174;
    svg.replaceChildren();
    svg.setAttribute("viewBox",`0 0 ${width} ${height}`);
    $("return-chart-badge").textContent=`${best.count.toLocaleString("en-US")} valid NPVs`;

    const sorted=[...values].sort((a,b)=>a-b),n=sorted.length,mean=sorted.reduce((sum,value)=>sum+value,0)/n;
    const sd=Math.sqrt(sorted.reduce((sum,value)=>sum+(value-mean)**2,0)/n);
    const iqr=quantileSorted(sorted,.75)-quantileSorted(sorted,.25),spread=sorted.at(-1)-sorted[0];
    const bandwidth=Math.max(1,spread/200,.9*(iqr>0?Math.min(sd,iqr/1.34):sd)*n**(-.2));
    const minimum=sorted[0]-3*bandwidth,maximum=sorted.at(-1)+3*bandwidth;
    const xAt=value=>left+(width-left-right)*(value-minimum)/(maximum-minimum);
    const samples=[];let start=0,end=0;
    for(let i=0;i<=150;i++){
      const value=minimum+(maximum-minimum)*i/150;
      while(start<n&&sorted[start]<value-4*bandwidth)start++;
      end=Math.max(end,start);
      while(end<n&&sorted[end]<=value+4*bandwidth)end++;
      let density=0;
      for(let j=start;j<end;j++)density+=Math.exp(-.5*((value-sorted[j])/bandwidth)**2);
      samples.push({value,density});
    }
    const peak=Math.max(...samples.map(point=>point.density),1);
    const curve=samples.map(({value,density},index)=>(index?"L":"M")+xAt(value).toFixed(2)+" "+(bottom-(bottom-top)*density/peak).toFixed(2)).join(" ");
    const area=curve+` L ${width-right} ${bottom} L ${left} ${bottom} Z`;
    const cutoff=quantileSorted(sorted,.05),defs=svgElement("defs"),clip=svgElement("clipPath",{id:"recommended-npv-tail"});
    clip.append(svgElement("rect",{x:left,y:top-2,width:xAt(cutoff)-left,height:bottom-top+2}));
    defs.append(clip);svg.append(defs);
    svg.append(svgElement("path",{d:area,fill:"#e6efe3"}),svgElement("path",{d:area,fill:"#ead4b2","clip-path":"url(#recommended-npv-tail)"}));
    svg.append(svgElement("line",{x1:left,y1:bottom,x2:width-right,y2:bottom,stroke:"#9caf9e"}));
    const metrics=[
      {id:"cvar5",label:"CVaR₅",color:"#8b5725",dash:"2 3"},
      {id:"median",label:"Median",color:"#25674a",dash:"6 4"},
      {id:"p95",label:"P95",color:"#326e85",dash:"10 3 2 3"}
    ];
    for(const {id,label,color,dash} of metrics){
      const value=best[id],x=xAt(value),line=svgElement("line",{x1:x,y1:top,x2:x,y2:bottom,stroke:color,"stroke-width":1.7,"stroke-dasharray":dash});
      const title=svgElement("title");title.textContent=`${label}: ${brl(value, value!==0&&Math.abs(value)<1?2:0)}/ha`;line.append(title);svg.append(line);
      $(`return-value-${id}`).textContent=brl(value,0)+"/ha";
    }
    svg.append(svgElement("path",{d:curve,fill:"none",stroke:"#377354","stroke-width":2.5,"stroke-linejoin":"round","stroke-linecap":"round"}));
    for(let i=0;i<=4;i++){
      const value=minimum+(maximum-minimum)*i/4,x=xAt(value);
      svg.append(svgElement("line",{x1:x,y1:bottom,x2:x,y2:bottom+5,stroke:"#9caf9e"}));
      const tick=svgElement("text",{x,y:bottom+21,"text-anchor":"middle",fill:"#455c50","font-size":12});
      tick.textContent=chartMoney(value);svg.append(tick);
    }
    const axis=svgElement("text",{x:width/2,y:height-6,"text-anchor":"middle",fill:"#455c50","font-size":12});
    axis.textContent="Net present value (R$/ha)";svg.append(axis);
    svg.setAttribute("aria-label",`Smoothed net present value distribution for ${routeLabel(best)}, based on ${n} valid scenarios. `+metrics.map(({id,label})=>`${label}: ${brl(best[id],0)} per hectare`).join("; "));
    $("return-chart-summary").textContent=`Shaded area: lower tail up to the 5th percentile. CVaR₅ averages the ${best.tailCount.toLocaleString("en-US")} lowest valid outcomes; P95 is the 95th percentile.`+(n<rankingSupportSettings.full_score_vpl_samples?" Small sample; the tail estimates can vary substantially.":"");
  }

  function renderEnvironmentOutcomeChart(frames,config) {
    const svg=$(config.svgId),detail=$(config.detailId),width=640,height=260,left=42,right=12,top=20,bottom=216,plotWidth=width-left-right,plotHeight=bottom-top;
    svg.replaceChildren();detail.textContent="";
    if(frames.length<2)return;
    const counts=frames.map(frame=>frame?.[config.dimension]||{}),totals=counts.map(row=>config.series.reduce((sum,item)=>sum+Number(row[item.id]||0),0)),last=counts.length-1;
    const xAt=index=>left+plotWidth*index/last,yAt=fraction=>bottom-plotHeight*fraction;
    svg.setAttribute("viewBox",`0 0 ${width} ${height}`);
    let lower=Array(counts.length).fill(0);
    for(const item of config.series) {
      const upper=counts.map((row,index)=>lower[index]+Number(row[item.id]||0)/Math.max(1,totals[index]));
      const topPath=upper.map((value,index)=>(index?"L":"M")+xAt(index).toFixed(2)+" "+yAt(value).toFixed(2)).join(" ");
      const bottomPath=lower.map((value,index)=>({value,index})).reverse().map(({value,index})=>"L"+xAt(index).toFixed(2)+" "+yAt(value).toFixed(2)).join(" ");
      svg.append(svgElement("path",{d:topPath+" "+bottomPath+" Z",fill:item.color,"fill-opacity":.9,stroke:"#fff","stroke-width":.45}));lower=upper;
    }
    for(const value of [0,.25,.5,.75,1]) {
      const y=yAt(value);svg.append(svgElement("line",{x1:left,y1:y,x2:width-right,y2:y,stroke:"#fff","stroke-width":1,"stroke-opacity":.8}));
      const label=svgElement("text",{x:left-7,y:y+3,"text-anchor":"end",fill:"#68756c","font-size":9});label.textContent=Math.round(value*100)+"%";svg.append(label);
    }
    for(let year=0;year<=horizon;year++) {
      const index=Math.round(last*year/horizon),x=xAt(index);svg.append(svgElement("line",{x1:x,y1:top,x2:x,y2:bottom,stroke:"#fff","stroke-width":1,"stroke-opacity":.65}));
      const label=svgElement("text",{x,y:bottom+19,"text-anchor":"middle",fill:"#68756c","font-size":9});label.textContent=year===horizon?"60 mo":String(year*12);svg.append(label);
    }
    const axis=svgElement("text",{x:width-right,y:11,"text-anchor":"end",fill:"#68756c","font-size":9});axis.textContent="% of scenarios";svg.append(axis);
    const cursor=svgElement("line",{x1:xAt(last),y1:top,x2:xAt(last),y2:bottom,stroke:"#263e31","stroke-width":1.2,"stroke-dasharray":"3 3","pointer-events":"none"});svg.append(cursor);
    const showPeriod=index=>{
      const selected=clamp(Math.round(index),0,last),row=counts[selected],total=Math.max(1,totals[selected]),month=selected*horizonMonths/last;
      svg.dataset.period=String(selected);
      cursor.setAttribute("x1",xAt(selected));cursor.setAttribute("x2",xAt(selected));
      detail.textContent=`Month ${fmt(month,1)} · ${totals[selected].toLocaleString("en-US")} scenarios · `+config.series.map(item=>`${item.label} ${pct(Number(row[item.id]||0)/total)}`).join(" · ");
    };
    const overlay=svgElement("rect",{x:left,y:top,width:plotWidth,height:plotHeight,fill:"transparent",style:"cursor:crosshair"});svg.append(overlay);
    const fromPointer=event=>{const rect=svg.getBoundingClientRect(),x=(event.clientX-rect.left)*width/Math.max(1,rect.width);showPeriod((x-left)/plotWidth*last);};
    overlay.addEventListener("pointermove",fromPointer);overlay.addEventListener("pointerdown",fromPointer);
    svg.onkeydown=event=>{
      const current=Number(svg.dataset.period||last);let next=current;
      if(event.key==="ArrowLeft")next=current-1;else if(event.key==="ArrowRight")next=current+1;else if(event.key==="Home")next=0;else if(event.key==="End")next=last;else return;
      event.preventDefault();next=clamp(next,0,last);svg.dataset.period=String(next);showPeriod(next);
    };
    showPeriod(last);
  }

  function renderFarmerResultCharts(run,best) {
    const sample=run.rotationSamples.get(best.key),frames=rotationEnvironmentFrames(sample);
    renderReturnChart(best,sample.values);
    for(const id of ["water","soil"])$(`farmer-${id}-badge`).textContent=`${best.frequency.toLocaleString("en-US")} scenarios`;
    renderEnvironmentOutcomeChart(frames,{svgId:"farmer-water-chart",detailId:"farmer-water-period",dimension:"water",series:[{id:"water_high",label:"Good",color:"#4b91ad"},{id:"water_medium",label:"Fair",color:"#d6ad51"},{id:"water_low",label:"Bad",color:"#cf7b6b"}]});
    renderEnvironmentOutcomeChart(frames,{svgId:"farmer-soil-chart",detailId:"farmer-soil-period",dimension:"soil",series:[{id:"soil_good",label:"Good",color:"#5c8d5a"},{id:"soil_regular",label:"Fair",color:"#c59a50"},{id:"soil_degraded",label:"Bad",color:"#b97657"}]});
  }

  function showFarmerResult() {
    const run=simulationSession,best=run?.recommendedRoute;
    if(!best) {
      showFarmerError(`A recommendation needs at least ${minimumRecommendedVplSamples} valid NPVs for one sequence. Try more scenarios or explore the results under Settings → Advanced.`);
      return;
    }
    const city=selectedCityData(),environment=Number($("farmer-priority").value),finance=100-environment;
    const path=$("farmer-rotation-path"); path.replaceChildren();
    const crops=best.routeEvents.crops||[];
    $("result-title").textContent=crops.length>1?"A crop rotation to grow more and care for the land":"A plan to grow more and care for the land";
    document.querySelector(".recommendation-card h2").textContent=crops.length>1?"Your suggested sequence":"Your suggested management plan";
    let streak=0;
    crops.forEach((crop,index)=>{
      streak=crop===crops[index-1]?streak+1:1;
      const penalty=1-repeatedCropYieldMultiplier(crop,streak);
      const item=document.createElement("div"); item.className="rotation-crop"+(index===0?" is-current":""); item.style.animationDelay=`${index*.22}s`;
      item.innerHTML=`${cropArtwork(crop)}<strong>${farmerCropName(crop)}</strong><small>${index===0?"Current crop":`Planting ${index+1}`}</small>${penalty>0?`<small>−${pct(penalty)} yield at harvest</small>`:""}`; path.append(item);
    });
    $("result-income").innerHTML=`${brl(best.median,0)} <small>/ha</small>`;
    $("result-income-detail").textContent=`Median present value over five years · ${best.count.toLocaleString("en-US")} ${best.count===1?"scenario":"scenarios"} with complete calculations${best.count<rankingSupportSettings.full_score_vpl_samples?" · small sample":""}.`;
    $("result-soil").textContent=soilFriendly(best.finalSocMean);
    $("result-soil-detail").textContent=`${fmt(best.finalSocMean,1)} g/kg of estimated organic carbon at the end of the cycle.`;
    const waterEntries=Object.entries(best.finalWaterCounts||{}).sort((a,b)=>b[1]-a[1]),waterId=waterEntries[0]?.[0]||"water_medium",waterShare=Number(waterEntries[0]?.[1]||0)/Math.max(1,best.finalEnvironmentCount);
    $("result-water").textContent=({water_low:"Low",water_medium:"Medium",water_high:"High"})[waterId]||"Medium";
    $("result-water-detail").textContent=`Most frequent final condition, seen in ${pct(waterShare)} of trajectories. Mean final water: ${pct(best.finalWaterFractionMean)} of capacity.`;
    const facts=[
      `${city.municipality} (${city.uf}): historical climate, soil, and municipal planting calendar.`,
      `Starting with ${farmerCropName(farmerUI.crop).toLowerCase()}, with priorities split ${finance}% returns and ${environment}% soil and water before fixed sample support.`,
      `${best.frequency.toLocaleString("en-US")} of ${run.completed.toLocaleString("en-US")} simulated scenarios followed this sequence; ${best.count.toLocaleString("en-US")} had a valid NPV.`,
      `Sample support: ${fmt(best.supportScore10,1)}/10, worth ${fmt(100*rankingSupportSettings.weight,0)}% of the ranking score. Full support takes ${rankingSupportSettings.full_score_vpl_samples} valid NPVs.`
    ];
    if(run.start==="sugarcane")facts.push(`Sugarcane starts at cut ${run.initialSugarcaneCut} of the modeled ${cycleRule("sugarcane").modeled_harvest_cuts} cuts.`);
    $("result-facts").innerHTML=facts.map(text=>`<li>${icon("check")}<span>${text}</span></li>`).join("");
    const alternatives=run.routeResults.filter(route=>route!==best&&route.count>=minimumRecommendedVplSamples).slice(0,3);
    const alternativeRoot=$("result-alternatives"); alternativeRoot.replaceChildren();
    if(!alternatives.length) alternativeRoot.textContent=`No other sequence reached ${minimumRecommendedVplSamples} valid NPVs.`;
    alternatives.forEach(route=>{ const item=document.createElement("div"); item.className="alternative-route"; const name=document.createElement("strong"); name.textContent=routeLabel(route); const value=document.createElement("span"); value.textContent=`${brl(route.median,0)}/ha`; item.append(name,value); alternativeRoot.append(item); });
    renderFarmerResultCharts(run,best);
    farmerUI.running=false; showFarmerScreen("result");
  }

  function showFarmerError(message) {
    farmerUI.running=false;
    $("screen-simulation").hidden=true;
    $("farmer-error-message").textContent=message;
    $("farmer-error").hidden=false;
  }

  async function watchFarmerSimulation(token) {
    const minimumAnimation=new Promise(resolve=>setTimeout(resolve,3200));
    while(token===farmerUI.runToken) {
      const state=simulationSession;
      updateSimulationProgress(Number(state?.completed||0));
      if(state && !state.running) {
        if(state.completed>=farmerUI.target && state.routeResults) { await minimumAnimation; if(token===farmerUI.runToken) showFarmerResult(); }
        else if(state.completed<farmerUI.target) showFarmerError("The simulation was interrupted. Try again or adjust the number of scenarios in the settings.");
        return;
      }
      await new Promise(resolve=>requestAnimationFrame(resolve));
    }
  }

  function runFarmerAnalysis() {
    if(!farmerUI.city||!farmerUI.crop) return;
    farmerUI.target=Number($("config-trajectories").value)||100000;
    farmerUI.running=true; farmerUI.runToken++; farmerUI.startedAt=Date.now(); renderGrowth.lastBucket=null;
    $("initial-crop-select").value=farmerUI.crop;
    $("technical-sugarcane-cut-field").hidden=farmerUI.crop!=="sugarcane";
    if(farmerUI.crop==="sugarcane")$("initial-sugarcane-cut").value=$("farmer-sugarcane-cut").value;
    $("ranking-environment-weight").value=$("farmer-priority").value;
    $("simulation-seed").value=$("config-seed").value;
    $("simulation-title").textContent=`We're growing possibilities for ${farmerCropName(farmerUI.crop).toLowerCase()}`;
    updateSimulationProgress(0); renderGrowth(0); showFarmerScreen("simulation");
    startSimulation(currentSeed(),farmerUI.target,true);
    void watchFarmerSimulation(farmerUI.runToken);
  }

  document.querySelectorAll("[data-profile]").forEach(node=>{
    node.addEventListener("click",()=>selectCity(node.dataset.profile));
    if(node.classList.contains("city-marker")) node.addEventListener("keydown",event=>{ if(event.key==="Enter"||event.key===" "){event.preventDefault();selectCity(node.dataset.profile);} });
  });
  document.querySelectorAll(".crop-choice").forEach(node=>node.addEventListener("click",()=>selectCrop(node.dataset.crop)));
  const modeledCuts=cycleRule("sugarcane").modeled_harvest_cuts;
  for(let cut=1;cut<=modeledCuts;cut++){
    const label=cut===1?"Cut 1 · plant cane":`Cut ${cut} · ratoon cane`;
    $("farmer-sugarcane-cut").add(new Option(label,String(cut)));
  }
  $("farmer-sugarcane-cut-note").textContent=`Choose the next cut, not the last completed one. The model allows rotation after cut ${modeledCuts} and uses regional yield and costs for each cut.`;
  document.querySelectorAll("[data-crop-art]").forEach(node=>node.innerHTML=cropArtwork(node.dataset.cropArt));
  document.querySelectorAll("[data-go]").forEach(node=>node.addEventListener("click",()=>showFarmerScreen(node.dataset.go)));
  $("location-next").addEventListener("click",()=>showFarmerScreen("crop"));
  $("crop-next").addEventListener("click",()=>showFarmerScreen("priority"));
  $("farmer-priority").addEventListener("input",updatePriority);
  $("run-farmer-simulation").addEventListener("click",runFarmerAnalysis);
  $("retry-simulation").addEventListener("click",runFarmerAnalysis);
  $("adjust-priority").addEventListener("click",()=>showFarmerScreen("priority"));
  $("restart-analysis").addEventListener("click",()=>{ farmerUI.crop=null; $("farmer-sugarcane-cut-field").hidden=true; $("farmer-sugarcane-cut").value="1"; document.querySelectorAll(".crop-choice").forEach(node=>{node.classList.remove("is-selected");node.setAttribute("aria-pressed","false");}); $("crop-next").disabled=true; showFarmerScreen("location"); });
  function showMethodLevel(level) {
    const technical=level==="technical";
    for(const name of ["simple","technical"]) {
      const selected=name===level,tab=$(`method-tab-${name}`);
      $(`method-panel-${name}`).hidden=!selected;
      tab.setAttribute("aria-selected",String(selected));tab.tabIndex=selected?0:-1;
    }
    $("methodology-title").textContent=technical?"The decision engine, end to end.":"A simple answer. A deeper model.";
    $("methodology-intro").textContent=technical?"Climate, crops, constraints, and cash flow—connected in one stochastic simulation.":"Five ideas work together to turn local data into your recommendation.";
  }
  for(const level of ["simple","technical"]) $(`method-tab-${level}`).addEventListener("click",()=>showMethodLevel(level));
  document.querySelector(".method-tabs").addEventListener("keydown",event=>{
    if(!["ArrowLeft","ArrowRight","Home","End"].includes(event.key))return;
    event.preventDefault();const current=$("method-tab-technical").getAttribute("aria-selected")==="true";
    const next=event.key==="Home"?"simple":event.key==="End"?"technical":current?"simple":"technical";
    showMethodLevel(next);$(`method-tab-${next}`).focus();
  });
  $("open-methodology").addEventListener("click",()=>{
    const count=farmerUI.target.toLocaleString("en-US"),routes=simulationSession?.routeResults?.length||0;
    $("method-scenario-count").textContent=`${count} futures`;$("underhood-scenarios").textContent=`${count} trajectories`;
    $("underhood-routes").textContent=`${routes.toLocaleString("en-US")} ranked routes`;
    $("underhood-priority").textContent=`λ = ${(Number($("farmer-priority").value)/100).toFixed(2)}`;
    $("underhood-support-rule").textContent=`A recommendation requires at least ${minimumRecommendedVplSamples} valid NPVs per route. Sample support is worth ${fmt(100*rankingSupportSettings.weight,0)}% of the score and reaches its maximum at ${rankingSupportSettings.full_score_vpl_samples} valid NPVs.`;
    showMethodLevel("simple");$("methodology-dialog").showModal();
  });
  $("close-methodology").addEventListener("click",()=>$("methodology-dialog").close());
  $("methodology-dialog").addEventListener("click",event=>{ if(event.target===$("methodology-dialog")) $("methodology-dialog").close(); });
  $("open-settings").addEventListener("click",()=>{
    $("config-seed").value=$("simulation-seed").value;
    $("settings-dialog").showModal();
  });
  $("close-settings").addEventListener("click",()=>$("settings-dialog").close());
  $("settings-dialog").addEventListener("click",event=>{ if(event.target===$("settings-dialog")) $("settings-dialog").close(); });
  $("config-trajectories").addEventListener("change",()=>{ farmerUI.target=Number($("config-trajectories").value); $("simulation-count-summary").textContent=`${farmerUI.target.toLocaleString("en-US")} scenarios`; });
  $("config-seed").addEventListener("input",()=>{ $("simulation-seed").value=$("config-seed").value; });
  $("simulation-seed").addEventListener("input",()=>{ $("config-seed").value=$("simulation-seed").value; });
  updatePriority(); renderGrowth(0);
})();
