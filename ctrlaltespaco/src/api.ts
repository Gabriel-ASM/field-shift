import type { Boundary, ChainMatrix, Profile, ProfileSummary, RunResult, RuntimeConfig, ScenarioRequest } from "./types.ts";

const HORIZON_DAYS = 1825;

export class ApiError extends Error {}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(path, init);
  if (!response.ok) throw new ApiError(await failureMessage(path, response));
  return (await response.json()) as T;
}

async function failureMessage(path: string, response: Response): Promise<string> {
  const body = (await response.json().catch(() => null)) as { detail?: unknown } | null;
  const detail = body?.detail;
  const text = typeof detail === "string" ? detail : detail ? JSON.stringify(detail) : response.statusText;
  return `${path}: ${text}`;
}

export const getConfig = () => request<RuntimeConfig>("/config");
export const listProfiles = () => request<ProfileSummary[]>("/profiles");
export const getProfile = (id: string) => request<Profile>(`/profiles/${encodeURIComponent(id)}`);
export const getMatrix = (id: string) => request<ChainMatrix>(`/profiles/${encodeURIComponent(id)}/chain/matrix`);
export const getStates = () => request<Boundary>("/geo/states");
export const getMunicipality = (id: string) => request<Boundary>(`/geo/profiles/${encodeURIComponent(id)}`);

export interface RunOptions {
  profile: string;
  seed: number;
  trajectories: number;
  tracks: number;
  scenarios: ScenarioRequest[];
}

export function createRun({ profile, seed, trajectories, tracks, scenarios }: RunOptions): Promise<RunResult> {
  const body = { profile, seed, trajectories, horizon_days: HORIZON_DAYS, scenarios };
  return request<RunResult>(`/runs?tracks=${tracks}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
}
