import type { ChainMatrix, ScenarioRequest } from "./types.ts";

const FALLOW_STATE = "fallow:skip_stages";

export const cropOf = (state: string) => state.split(":")[0]!;

/** Crops that can be planted in this profile, in chain order. */
export function chainCrops(matrix: ChainMatrix): string[] {
  return matrix.states.map(cropOf).filter((crop) => crop !== "fallow");
}

/** The starting crop followed by its most likely different successor: the rotation the data itself suggests. */
export function suggestedRotation(matrix: ChainMatrix, crop: string = cropOf(matrix.initial_state)): string[] {
  const start = `${crop}:skip_stages`;
  const row = matrix.rows.find((candidate) => candidate.from === start);
  const successors = matrix.states
    .map((state, index) => ({ state, probability: row?.cells[index]?.probability ?? 0 }))
    .filter(({ state, probability }) => state !== start && probability > 0)
    .sort((a, b) => b.probability - a.probability);
  return [cropOf(start), ...successors.slice(0, 1).map(({ state }) => cropOf(state))];
}

/** Both scenarios start from `start`; the rotation then follows its sequence. */
export function scenariosFor(sequence: string[], start: string): ScenarioRequest[] {
  const initial_state = `${start}:skip_stages`;
  return [
    { id: "region", label: "What the region usually does", initial_state, policy: { kind: "markov" } },
    { id: "rotation", initial_state, label: `Fixed rotation: ${sequence.map((crop) => crop.replace(/_/g, " ")).join(" → ")}`,
      policy: { kind: "rotation", sequence, fallback: FALLOW_STATE } },
  ];
}
