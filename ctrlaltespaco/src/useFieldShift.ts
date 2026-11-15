import { useCallback, useEffect, useState } from "react";
import { createRun, getConfig, getMunicipality, getProfile, getRunChoices, getStates, listProfiles } from "./api.ts";
import { regionScenario } from "./scenarios.ts";
import { playhead } from "./state/playhead.ts";
import type { Boundary, Profile, RunChoices, RunResult, RuntimeConfig } from "./types.ts";

export interface World {
  config: RuntimeConfig;
  profiles: Profile[];
  states: Boundary;
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

export type Step = "location" | "crop" | "priority" | "simulation" | "result";
export const STEPS: Step[] = ["location", "crop", "priority", "simulation", "result"];

export interface Place {
  profile: Profile;
  municipality: Boundary;
  choices: RunChoices;
}

export interface Journey {
  step: Step;
  place: Place | null;
  crop: string | null;
  /** Next harvest of standing cane; used only when the crop is sugarcane. */
  caneCut: number;
  /** Share of the score given to soil and water. */
  weight: number;
  seed: number;
  run: RunResult | null;
  error: string | null;
  go: (step: Step) => void;
  choosePlace: (profile: Profile) => void;
  chooseCrop: (crop: string) => void;
  chooseCaneCut: (cut: number) => void;
  setWeight: (weight: number) => void;
  setSeed: (seed: number) => void;
  simulate: () => void;
  restart: () => void;
}

/** The linear journey: place, crop, priority, simulation, result. */
export function useJourney(world: World | null): Journey {
  const [step, go] = useState<Step>("location");
  const [place, setPlace] = useState<Place | null>(null);
  const [crop, setCrop] = useState<string | null>(null);
  const [caneCut, setCaneCut] = useState(1);
  const [weight, setWeight] = useState(0.2);
  const [seed, setSeed] = useState(2026);
  const [run, setRun] = useState<RunResult | null>(null);
  const [simulated, setSimulated] = useState("");
  const [error, setError] = useState<string | null>(null);

  const choosePlace = useCallback((profile: Profile) => {
    setError(null);
    setRun(null);
    setCrop(null);
    Promise.all([getMunicipality(profile.id), getRunChoices(profile.id)]).then(([municipality, choices]) => {
      setPlace({ profile, municipality, choices });
      setWeight(choices.ranking.environment_weight.default_weight);
    }, (failure) => setError(message(failure)));
  }, []);

  const chooseCrop = useCallback((chosen: string) => {
    setCrop(chosen);
    setRun(null);
  }, []);

  const chooseCaneCut = useCallback((cut: number) => {
    setCaneCut(cut);
    setRun(null);
  }, []);

  /** Runs the engine, unless this place, crop and seed were already simulated: priorities only re-rank. */
  const simulate = useCallback(() => {
    if (!world || !place || !crop) return;
    const key = `${place.profile.id}|${crop}|${caneCut}|${seed}`;
    if (run && simulated === key) return go("result");
    go("simulation");
    setError(null);
    createRun({ profile: place.profile.id, seed, scenarios: [regionScenario(crop, caneCut)], ...world.config.run }).then((result) => {
      playhead.reset(result.clock.periods);
      setRun(result);
      setSimulated(key);
      go("result");
    }, (failure) => setError(message(failure)));
  }, [world, place, crop, caneCut, seed, run, simulated]);

  const restart = useCallback(() => {
    setPlace(null);
    setCrop(null);
    setRun(null);
    setError(null);
    go("location");
  }, []);

  return { step, place, crop, caneCut, weight, seed, run, error, go, choosePlace, chooseCrop, chooseCaneCut, setWeight, setSeed, simulate, restart };
}
