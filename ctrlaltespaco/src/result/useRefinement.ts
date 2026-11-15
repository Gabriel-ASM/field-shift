/** The best candidates of a run, simulated again as fixed rotations with the same seed.
 *
 *  In the chain run a sequence is only the trajectories that happened to follow it, often 20 to 45 of 100,000, so
 *  its numbers and even the winner move with the seed. Planting it on purpose in REFINE_TRAJECTORIES scenarios
 *  gives each candidate a full sample. Results are kept by sequence, so new candidates (after the farmer moves
 *  a slider) are the only ones simulated again. */

import { useEffect, useRef, useState } from "react";
import { runJob, type Progress } from "../runJob.ts";
import { routeKey, type RankedRoute } from "../ranking.ts";
import { rotationScenario } from "../scenarios.ts";
import type { Route } from "../types.ts";

export const REFINE_TRAJECTORIES = 10_000;
export const REFINE_CANDIDATES = 5;

/** A candidate's own result, and where to ask for its detail (job, scenario index; every trajectory). */
export interface Refined {
  route: Route;
  job: string;
  scenario: number;
}

export interface RefineRequest {
  profile: string;
  seed: number;
  caneCut: number;
  /** Identifies the chain run: results of another run are dropped. */
  run: string | null;
}

export interface Refinement {
  refined: Map<string, Refined>;
  progress: Progress | null;
  error: string | null;
}

function scenarioId(index: number) {
  return `candidate-${index}`;
}

interface State extends Refinement {
  run: string | null;
}

const fresh = (run: string | null): State => ({ run, refined: new Map(), progress: null, error: null });

export function useRefinement(request: RefineRequest, candidates: RankedRoute[]): Refinement {
  const [stored, setState] = useState<State>(() => fresh(request.run));
  const state = stored.run === request.run ? stored : fresh(request.run);   // results of another run are dropped
  const busy = useRef<string | null>(null);                                  // run with a job in flight
  const missing = candidates.map(({ route }) => route.crops).filter((crops) => !state.refined.has(crops.join(",")));
  const missingKey = missing.map((crops) => crops.join(",")).join("|");
  useEffect(() => {
    const run = request.run;
    if (!run || !missing.length || busy.current === run || state.error) return;
    busy.current = run;
    const update = (change: (current: State) => State) => setState((previous) => change(previous.run === run ? previous : fresh(run)));
    const scenarios = missing.map((crops, index) => rotationScenario(scenarioId(index), crops, request.caneCut));
    runJob({ profile: request.profile, seed: request.seed, trajectories: REFINE_TRAJECTORIES, tracks: 0, scenarios },
      (progress) => update((current) => ({ ...current, progress }))).then(
      ({ job, result }) => {
        update((current) => {
          const refined = new Map(current.refined);
          result.scenarios.forEach((scenario, index) => {
            const crops = missing[index]!;
            refined.set(crops.join(","), { route: { ...scenario.overall, crops }, job, scenario: index });
          });
          return { ...current, refined, progress: null };
        });
        if (busy.current === run) busy.current = null;
      },
      (failure: unknown) => {
        update((current) => ({ ...current, progress: null, error: failure instanceof Error ? failure.message : String(failure) }));
        if (busy.current === run) busy.current = null;
      },
    );
    // `missingKey` stands for the candidates still to simulate.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [request.run, missingKey, state.error]);
  return state;
}

/** The candidates' own routes, once every one of them is refined; null while some are still running. */
export function refinedRoutes(candidates: RankedRoute[], refinement: Refinement): Route[] | null {
  const routes = candidates.map(({ route }) => refinement.refined.get(routeKey(route))?.route);
  return routes.every(Boolean) && routes.length ? (routes as Route[]) : null;
}
