import type { ScenarioRequest } from "./types.ts";

/** The scenario the journey simulates: what the region usually does, starting from the farmer's crop.
 *  Standing cane also says which cut comes next. */
export function regionScenario(start: string, caneCut = 2): ScenarioRequest {
  const scenario: ScenarioRequest = { id: "region", label: "What the region usually does", initial_state: `${start}:skip_stages`, policy: { kind: "markov" } };
  return start === "sugarcane" ? { ...scenario, initial_sugarcane_cut: caneCut } : scenario;
}
