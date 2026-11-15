import { BUNDLE_VERSION, DEV, RELOAD_MESSAGE, VERSION_HEADER } from "./version.ts";
import type { Boundary, ChainMatrix, JobView, PlantingWindows, Profile, ProfileSummary, RouteDetail, RunChoices, RunResult, RuntimeConfig, ScenarioRequest } from "./types.ts";

const HORIZON_DAYS = 1825;

export class ApiError extends Error {}

/** The API runs another build than this bundle: the page must be reloaded. */
export class OutdatedError extends Error {
  constructor(readonly server: string) {
    super(RELOAD_MESSAGE);
  }
}

/** Every request names the bundle's build; the run routes answer 409, with their own build, when it differs. */
async function request<T>(path: string, init: RequestInit = {}): Promise<T> {
  const headers = new Headers(init.headers);
  headers.set(VERSION_HEADER, BUNDLE_VERSION);
  const response = await fetch(path, { ...init, headers });
  const server = response.headers.get(VERSION_HEADER);
  if (response.status === 409 && server) throw new OutdatedError(server);
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

/** The API's build now, never from a cache: it may have been redeployed since the page loaded. */
export const getServerVersion = async () => (await request<RuntimeConfig>("/config", { cache: "no-store" })).version ?? DEV;
export const listProfiles = () => request<ProfileSummary[]>("/profiles");
export const getProfile = (id: string) => request<Profile>(`/profiles/${encodeURIComponent(id)}`);
export const getPlantingWindows = (id: string) => request<PlantingWindows>(`/profiles/${encodeURIComponent(id)}/planting-windows`);
export const getMatrix = (id: string) => request<ChainMatrix>(`/profiles/${encodeURIComponent(id)}/chain/matrix`);
export const getRunChoices = (id: string) => request<RunChoices>(`/runs/options/${encodeURIComponent(id)}`);
export const getStates = () => request<Boundary>("/geo/states");
export const getMunicipality = (id: string) => request<Boundary>(`/geo/profiles/${encodeURIComponent(id)}`);

export interface RunOptions {
  profile: string;
  seed: number;
  trajectories: number;
  tracks: number;
  scenarios: ScenarioRequest[];
}

function runBody({ profile, seed, trajectories, scenarios }: RunOptions): string {
  return JSON.stringify({ profile, seed, trajectories, horizon_days: HORIZON_DAYS, scenarios });
}

export function createRun(options: RunOptions): Promise<RunResult> {
  return request<RunResult>(`/runs?tracks=${options.tracks}`, {
    method: "POST", headers: { "Content-Type": "application/json" }, body: runBody(options),
  });
}

/** Starts the run in the background; poll getJob for the trajectories done and, at the end, the result. */
export function startJob(options: RunOptions): Promise<{ id: string; total: number }> {
  return request(`/runs/jobs?tracks=${options.tracks}`, {
    method: "POST", headers: { "Content-Type": "application/json" }, body: runBody(options),
  });
}

export const getJob = (id: string) => request<JobView>(`/runs/jobs/${encodeURIComponent(id)}`);

/** Water and soil every period, year-end charts and some trajectories of one route of a finished job;
 *  `crops` null takes every trajectory of the scenario (a fixed rotation). */
export function getRoute(job: string, crops: string[] | null, scenario = 0): Promise<RouteDetail> {
  const route = crops ? `&crops=${encodeURIComponent(crops.join(","))}` : "";
  return request<RouteDetail>(`/runs/jobs/${encodeURIComponent(job)}/route?scenario=${scenario}${route}`);
}
