import { useCallback, useEffect, useState } from "react";
import { createRun, getConfig, getMatrix, getMunicipality, getProfile, getStates, listProfiles } from "./api.ts";
import { chainCrops, scenariosFor, suggestedRotation } from "./scenarios.ts";
import { playhead } from "./state/playhead.ts";
import type { Boundary, Profile, RunResult, RuntimeConfig } from "./types.ts";

export interface World {
  config: RuntimeConfig;
  profiles: Profile[];
  states: Boundary;
}

export interface Selection {
  profile: Profile;
  municipality: Boundary;
  crops: string[];
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
  seed: number;
  run: RunResult | null;
  running: boolean;
  error: string | null;
  select: (profile: Profile) => void;
  setSequence: (sequence: string[]) => void;
  setSeed: (seed: number) => void;
  simulate: () => void;
}

/** The selected profile and its simulation. Selecting a profile runs it with the rotation its chain suggests. */
export function useSimulation(world: World | null): Simulation {
  const [selection, setSelection] = useState<Selection | null>(null);
  const [sequence, setSequence] = useState<string[]>([]);
  const [seed, setSeed] = useState(2026);
  const [run, setRun] = useState<RunResult | null>(null);
  const [running, setRunning] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const start = useCallback(async (profile: string, rotation: string[], runSeed: number) => {
    if (!world) return;
    setRunning(true);
    setError(null);
    try {
      const result = await createRun({ profile, seed: runSeed, scenarios: scenariosFor(rotation), ...world.config.run });
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
    Promise.all([getMatrix(profile.id), getMunicipality(profile.id)]).then(([matrix, municipality]) => {
      const rotation = suggestedRotation(matrix);
      setSelection({ profile, municipality, crops: chainCrops(matrix) });
      setSequence(rotation);
      void start(profile.id, rotation, seed);
    }, (failure) => setError(message(failure)));
  }, [seed, start]);

  const simulate = useCallback(() => {
    if (selection) void start(selection.profile.id, sequence, seed);
  }, [selection, sequence, seed, start]);

  return { selection, sequence, seed, run, running, error, select, setSequence, setSeed, simulate };
}
