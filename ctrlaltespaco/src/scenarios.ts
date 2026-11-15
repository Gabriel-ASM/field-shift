import type { ScenarioRequest } from "./types.ts";

/** The scenario the journey simulates: what the region usually does, starting from the farmer's crop. */
export function regionScenario(start: string): ScenarioRequest {
  return { id: "region", label: "What the region usually does", initial_state: `${start}:skip_stages`, policy: { kind: "markov" } };
}
