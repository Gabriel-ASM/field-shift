import { useCallback, useEffect, useState } from "react";
import { getConfig, getMunicipality, getProfile, getRunChoices, getServerVersion, getStates, listProfiles, OutdatedError } from "./api.ts";
import { runJob, type Progress } from "./runJob.ts";
import { regionScenario } from "./scenarios.ts";
import { playhead } from "./state/playhead.ts";
import type { Boundary, Profile, RunChoices, RunResult, RuntimeConfig } from "./types.ts";
import { BUNDLE_VERSION, DEV, outdated } from "./version.ts";

export interface World {
  config: RuntimeConfig;
  profiles: Profile[];
  states: Boundary;
}

/** Seed of the first simulation of a place and crop, so that one is reproducible. */
const DEFAULT_SEED = 2026;

const message = (error: unknown) => (error instanceof Error ? error.message : String(error));

/** Everything loaded once: configuration, the profiles and the state boundaries. */
export function useWorld(): { world: World | null; error: string | null; addProfile: (profile: Profile) => void } {
  const [world, setWorld] = useState<World | null>(null);
  const [error, setError] = useState<string | null>(null);
  useEffect(() => {
    const load = async (): Promise<World> => {
      const [config, summaries, states] = await Promise.all([getConfig(), listProfiles(), getStates()]);
      return { config, states, profiles: await Promise.all(summaries.map(({ id }) => getProfile(id))) };
    };
    load().then(setWorld, (failure) => setError(message(failure)));
  }, []);
  /** A profile assembled on demand joins the ones loaded at the start. */
  const addProfile = useCallback((profile: Profile) => {
    setWorld((current) => current && { ...current, profiles: [...current.profiles.filter((item) => item.id !== profile.id), profile] });
  }, []);
  return { world, error, addProfile };
}

/** Resolves when the API runs this bundle's build; a run from an older bundle may misread the result. */
async function current(): Promise<void> {
  const server = await getServerVersion();
  if (outdated(BUNDLE_VERSION, server)) throw new OutdatedError(server);
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
  /** Share of the score given to soil and water (λ). */
  weight: number;
  /** Share of the economic score given to the high return P95 against the worst-case mean CVaR5 (α). */
  returnWeight: number;
  seed: number;
  run: RunResult | null;
  /** Job that produced `run`; route details are asked from it. */
  job: string | null;
  /** Trajectories simulated so far, while the engine runs. */
  progress: Progress | null;
  error: string | null;
  /** Build of the API as last seen (GET /config or a 409). */
  server: string;
  /** The API runs another build than this page: nothing more is run until the page is reloaded. */
  outdated: boolean;
  go: (step: Step) => void;
  choosePlace: (profile: Profile) => void;
  chooseCrop: (crop: string) => void;
  chooseCaneCut: (cut: number) => void;
  setWeight: (weight: number) => void;
  setReturnWeight: (weight: number) => void;
  setSeed: (seed: number) => void;
  simulate: () => void;
  restart: () => void;
}

/** The linear journey: place, crop, priority, simulation, result. */
export function useJourney(world: World | null): Journey {
  const [step, go] = useState<Step>("location");
  const [place, setPlace] = useState<Place | null>(null);
  const [crop, setCrop] = useState<string | null>(null);
  const [caneCut, setCaneCut] = useState(2);
  const [weight, setWeight] = useState(0.2);
  const [returnWeight, setReturnWeight] = useState(0.5);
  const [seed, setSeed] = useState(DEFAULT_SEED);
  const [run, setRun] = useState<RunResult | null>(null);
  const [job, setJob] = useState<string | null>(null);
  const [progress, setProgress] = useState<Progress | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [seen, setSeen] = useState<string | null>(null);
  const server = seen ?? world?.config.version ?? DEV;

  /** A failed run: if the API was redeployed meanwhile (a 409, or a job lost with the old process), ask for a reload. */
  const fail = useCallback((failure: unknown) => {
    if (failure instanceof OutdatedError) return setSeen(failure.server);
    getServerVersion().then((now) => {
      setSeen(now);
      if (!outdated(BUNDLE_VERSION, now)) setError(message(failure));
    }, () => setError(message(failure)));
  }, []);

  const choosePlace = useCallback((profile: Profile) => {
    setError(null);
    setRun(null);
    setCrop(null);
    Promise.all([getMunicipality(profile.id), getRunChoices(profile.id)]).then(([municipality, choices]) => {
      setPlace({ profile, municipality, choices });
      setWeight(choices.ranking.environment_weight.default_weight);
      setReturnWeight(choices.ranking.return_weight.default);
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

  /** Runs the engine, every time. The first run of a place and crop uses the default seed; asking again (after
   *  adjusting the priorities) simulates other scenarios, with a new seed. */
  const simulate = useCallback(() => {
    if (!world || !place || !crop) return;
    const next = run ? Math.floor(Math.random() * 2 ** 31) : DEFAULT_SEED;
    setSeed(next);
    go("simulation");
    setError(null);
    setProgress(null);
    const options = { profile: place.profile.id, seed: next, scenarios: [regionScenario(crop, caneCut)], ...world.config.run };
    current().then(() => runJob(options, setProgress)).then(({ job: id, result }) => {
      playhead.reset(result.clock.periods);
      setRun(result);
      setJob(id);
      go("result");
    }, fail);
  }, [world, place, crop, caneCut, run, fail]);

  const restart = useCallback(() => {
    setPlace(null);
    setCrop(null);
    setRun(null);
    setError(null);
    go("location");
  }, []);

  return { step, place, crop, caneCut, weight, returnWeight, seed, run, job, progress, error, server, outdated: outdated(BUNDLE_VERSION, server), go, choosePlace, chooseCrop, chooseCaneCut, setWeight, setReturnWeight, setSeed, simulate, restart };
}
