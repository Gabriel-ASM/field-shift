/** "What we considered" (showFarmerResult in producer.js), about the sequence on screen. */

import type { RankedRoute } from "../ranking.ts";
import type { RunResult, ScenarioResult } from "../types.ts";
import type { Journey } from "../useFieldShift.ts";
import { cropLabel } from "../ui/colors.ts";
import { count, percent } from "../ui/format.ts";

/** How many scenarios stand behind the numbers: the regional run's followers, or the sequence's own runs. */
function evidence(scenario: ScenarioResult, best: RankedRoute, regionalShare: number | null): string {
  const value = best.route.value!;
  if (regionalShare === null) {
    return `${count(best.route.trajectories)} of ${count(scenario.trajectories)} simulated scenarios followed this sequence; ${count(value.count)} had a valid NPV.`;
  }
  return `This sequence was planted on purpose in ${count(best.route.trajectories)} scenarios with the same climate draws; ${count(value.count)} had a valid NPV. In the regional run, ${percent(regionalShare)} of the scenarios followed it.`;
}

function facts(journey: Journey, run: RunResult, scenario: ScenarioResult, best: RankedRoute, regionalShare: number | null): string[] {
  const { name, uf } = journey.place!.profile.municipality;
  const { support } = run.ranking;
  const lines = [
    `${name} (${uf}): historical climate, soil, and municipal planting calendar.`,
    `Starting with ${cropLabel(scenario.initial_crop).toLowerCase()}, with priorities split ${percent(1 - journey.weight)} returns and ${percent(journey.weight)} soil and water before fixed sample support; money judged ${percent(journey.returnWeight)} on the high return (P95).`,
    evidence(scenario, best, regionalShare),
    `Sample support: ${best.support.toFixed(1)}/10, worth ${percent(support.weight)} of the ranking score. Full support takes ${count(support.full_score)} valid NPVs.`,
  ];
  if (scenario.initial_crop === "sugarcane") lines.push(`Sugarcane starts at cut ${journey.caneCut} of the modeled ${journey.place!.choices.sugarcane_cuts} cuts.`);
  lines.push(`Planting dates follow the MAPA ZARC windows; prices and costs come from IBGE and CONAB. Simulated on the ${run.device.toUpperCase()} in ${run.seconds} s, seed ${run.seed}.`);
  return lines;
}

export function Facts({ journey, run, scenario, best, regionalShare = null }: {
  journey: Journey; run: RunResult; scenario: ScenarioResult; best: RankedRoute; regionalShare?: number | null;
}) {
  return (
    <article className="result-panel">
      <h3>What we considered</h3>
      <ul className="result-facts">{facts(journey, run, scenario, best, regionalShare).map((line) => <li key={line}><span aria-hidden="true">✓</span><span>{line}</span></li>)}</ul>
    </article>
  );
}
