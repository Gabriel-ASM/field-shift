/** Shapes of the API answers the front uses. They mirror field_shift/api and field_shift/engines/summary.py. */

export interface RuntimeConfig {
  basemap: { tiles: string; max_zoom: number; attribution: string };
  cms: { url: string | null; token: string | null };
  run: { trajectories: number; tracks: number };
}

export interface ProfileSummary {
  id: string;
  label: string;
  municipality: { name: string; uf: string; ibge_code: string };
}

export interface Profile extends ProfileSummary {
  initial_node: { state: string; soil: Record<string, number>; climate: { lat: number; long: number } };
}

export interface ChainMatrix {
  initial_state: string;
  states: string[];
  rows: { from: string; cells: ({ probability: number } | null)[] }[];
}

export interface RankingSettings {
  minimum: number;
  maximum: number;
  break_even: number;
  minimum_scale: number;
  minimum_samples: number;
  environment_weight: { default_weight: number; maximum_weight: number; weight_step: number };
  soil_share: number;
  water_share: number;
  soil_reference: number;
  water_scale: number;
}

export interface RunChoices {
  crops: string[];
  initial_crops: string[];
  ranking: RankingSettings;
}

export interface Route {
  crops: string[];
  share: number;
  value: ValueSummary | null;
  final_carbon: number;
  final_water_multiplier: number;
}

export type Policy = { kind: "markov" } | { kind: "rotation"; sequence: string[]; fallback: string };

export interface ScenarioRequest {
  id: string;
  label: string;
  initial_state?: string;
  policy: Policy;
}

export interface ValueSummary {
  mean: number;
  p5: number;
  p50: number;
  p95: number;
  cvar5: number;
  count: number;
}

export interface Track {
  crop: string[];
  water_fraction: number[];
  carbon: number[];
  value: number[];
  climate_years: number[];
}

export interface ScenarioResult {
  id: string;
  label: string;
  initial_crop: string;
  trajectories: number;
  priced_share: number;
  value: ValueSummary | null;
  occupancy: Record<string, number>[];
  water: Record<string, number>[];
  carbon: { p5: number; p50: number; p95: number }[];
  routes: Route[];
  tracks: Track[];
}

export interface RunResult {
  profile: string;
  seed: number;
  device: "gpu" | "cpu";
  seconds: number;
  clock: { period_days: number; periods: number; horizon_years: number };
  crops: string[];
  ranking: RankingSettings;
  scenarios: ScenarioResult[];
}

export type Position = [longitude: number, latitude: number];

export interface Boundary {
  features: { geometry: { type: "Polygon"; coordinates: Position[][] } | { type: "MultiPolygon"; coordinates: Position[][][] } }[];
}
