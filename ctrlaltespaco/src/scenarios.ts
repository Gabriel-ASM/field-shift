import type { ScenarioRequest } from "./types.ts";

/** A candidate sequence planted on purpose: the crops in order, from the farmer's crop (fallow when blocked). */
export function rotationScenario(id: string, crops: string[], caneCut = 1): ScenarioRequest {
  const scenario: ScenarioRequest = { id, label: crops.join(" → "), initial_state: `${crops[0]}:skip_stages`,
    policy: { kind: "rotation", sequence: crops, fallback: "fallow:skip_stages" } };
  return crops[0] === "sugarcane" ? { ...scenario, initial_sugarcane_cut: caneCut } : scenario;
}

/** The scenario the journey simulates: what the region usually does, starting from the farmer's crop.
 *  Standing cane also says which cut comes next. */
export function regionScenario(start: string, caneCut = 1): ScenarioRequest {
  const scenario: ScenarioRequest = { id: "region", label: "What the region usually does", initial_state: `${start}:skip_stages`, policy: { kind: "markov" } };
  return start === "sugarcane" ? { ...scenario, initial_sugarcane_cut: caneCut } : scenario;
}
