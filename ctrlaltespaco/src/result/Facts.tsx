/** "What we considered" and "Other good options" (showFarmerResult in producer.js). */

import type { RankedRoute } from "../ranking.ts";
import type { RunResult, ScenarioResult } from "../types.ts";
import type { Journey } from "../useFieldShift.ts";
import { cropLabel } from "../ui/colors.ts";
import { count, money, percent } from "../ui/format.ts";

const ALTERNATIVES = 3;

function facts(journey: Journey, run: RunResult, scenario: ScenarioResult, best: RankedRoute): string[] {
  const { name, uf } = journey.place!.profile.municipality;
  const { support } = run.ranking;
  const value = best.route.value!;
  const lines = [
    `${name} (${uf}): historical climate, soil, and municipal planting calendar.`,
    `Starting with ${cropLabel(scenario.initial_crop).toLowerCase()}, with priorities split ${percent(1 - journey.weight)} returns and ${percent(journey.weight)} soil and water before fixed sample support; money judged ${percent(journey.returnWeight)} on the high return (P95).`,
    `${count(best.route.trajectories)} of ${count(scenario.trajectories)} simulated scenarios followed this sequence; ${count(value.count)} had a valid NPV.`,
    `Sample support: ${best.support.toFixed(1)}/10, worth ${percent(support.weight)} of the ranking score. Full support takes ${count(support.full_score)} valid NPVs.`,
  ];
  if (scenario.initial_crop === "sugarcane") lines.push(`Sugarcane starts at cut ${journey.caneCut} of the modeled ${journey.place!.choices.sugarcane_cuts} cuts.`);
  lines.push(`Planting dates follow the MAPA ZARC windows; prices and costs come from IBGE and CONAB. Simulated on the ${run.device.toUpperCase()} in ${run.seconds} s, seed ${run.seed}.`);
  return lines;
}

export function Facts({ journey, run, scenario, best }: { journey: Journey; run: RunResult; scenario: ScenarioResult; best: RankedRoute }) {
  return (
    <article className="result-panel">
      <h3>What we considered</h3>
      <ul className="result-facts">{facts(journey, run, scenario, best).map((line) => <li key={line}><span aria-hidden="true">✓</span><span>{line}</span></li>)}</ul>
    </article>
  );
}

/** The next sequences in the ranking that could also be recommended. */
export function Alternatives({ ranked, minimum }: { ranked: RankedRoute[]; minimum: number }) {
  const shown = ranked.filter(({ route }) => route.value!.count >= minimum).slice(0, ALTERNATIVES);
  return (
    <article className="result-panel">
      <h3>Other good options</h3>
      <div className="alternatives">
        {shown.length ? shown.map(({ route }) => (
          <div key={route.crops.join()} className="alternative-route"><strong>{route.crops.map(cropLabel).join(" → ")}</strong><span>{money(route.value!.p50)}/ha</span></div>
        )) : <p className="note">No other sequence reached {count(minimum)} valid NPVs.</p>}
      </div>
    </article>
  );
}
