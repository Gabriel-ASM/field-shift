import { useCallback, useEffect, useState } from "react";
import { createRun, getConfig, getMatrix, getMunicipality, getProfile, getRunChoices, getStates, listProfiles } from "./api.ts";
import { chainCrops, scenariosFor, suggestedRotation } from "./scenarios.ts";
import { playhead } from "./state/playhead.ts";
import type { Boundary, ChainMatrix, Profile, RunResult, RuntimeConfig } from "./types.ts";

export interface World {
  config: RuntimeConfig;
  profiles: Profile[];
  states: Boundary;
}

export interface Selection {
  profile: Profile;
  municipality: Boundary;
  matrix: ChainMatrix;
  crops: string[];
  /** Crops a simulation may start from. */
  startCrops: string[];
}

const message = (error: unknown) => (error instanceof Error ? error.message : String(error));

/** Everything loaded once: configuration, the profiles and the state boundaries. */
export function useWorld(): { world: World | null; error: string | null } {
  const [world, setWorld] = useState<World | null>(null);
  const [error, setError] = useState<string | null>(null);
  useEffect(() => {
    const load = async (): Promise<World> => {
      const [config, summaries, states] = await Promise.all([getConfig(), listProfiles(), getStates()]);
      return { config, states, profiles: await Promise.all(summaries.map(({ id }) => getProfile(id))) };
    };
    load().then(setWorld, (failure) => setError(message(failure)));
  }, []);
  return { world, error };
}

export interface Simulation {
  selection: Selection | null;
  sequence: string[];
  start: string;
  seed: number;
  run: RunResult | null;
  running: boolean;
  error: string | null;
  select: (profile: Profile) => void;
  setSequence: (sequence: string[]) => void;
  setStart: (crop: string) => void;
  setSeed: (seed: number) => void;
  simulate: () => void;
}

/** The selected profile and its simulation. Selecting a profile runs it with the rotation its chain suggests. */
export function useSimulation(world: World | null): Simulation {
  const [selection, setSelection] = useState<Selection | null>(null);
  const [sequence, setSequence] = useState<string[]>([]);
  const [start, setStartCrop] = useState("");
  const [seed, setSeed] = useState(2026);
  const [run, setRun] = useState<RunResult | null>(null);
  const [running, setRunning] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const launch = useCallback(async (profile: string, rotation: string[], crop: string, runSeed: number) => {
    if (!world) return;
    setRunning(true);
    setError(null);
    try {
      const result = await createRun({ profile, seed: runSeed, scenarios: scenariosFor(rotation, crop), ...world.config.run });
      playhead.reset(result.clock.periods);
      setRun(result);
    } catch (failure) {
      setError(message(failure));
    } finally {
      setRunning(false);
    }
  }, [world]);

  const select = useCallback((profile: Profile) => {
    setRun(null);
    Promise.all([getMatrix(profile.id), getMunicipality(profile.id), getRunChoices(profile.id)]).then(([matrix, municipality, choices]) => {
      const crop = choices.initial_crops[0] ?? choices.crops[0]!;
      const rotation = suggestedRotation(matrix, crop);
      setSelection({ profile, municipality, matrix, crops: chainCrops(matrix), startCrops: choices.initial_crops });
      setStartCrop(crop);
      setSequence(rotation);
      void launch(profile.id, rotation, crop, seed);
    }, (failure) => setError(message(failure)));
  }, [seed, launch]);

  /** Changing the starting crop also restarts the compared rotation from it. */
  const setStart = useCallback((crop: string) => {
    if (!selection) return;
    setStartCrop(crop);
    setSequence(suggestedRotation(selection.matrix, crop));
  }, [selection]);

  const simulate = useCallback(() => {
    if (selection) void launch(selection.profile.id, sequence, start, seed);
  }, [selection, sequence, start, seed, launch]);

  return { selection, sequence, start, seed, run, running, error, select, setSequence, setStart, setSeed, simulate };
}
