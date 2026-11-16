/** Shapes of the API answers the front uses. They mirror field_shift/api and field_shift/engines/summary.py. */

export interface RuntimeConfig {
  /** Build of the API (the commit), "dev" outside an image. Absent from APIs older than the check. */
  version?: string;
  basemap: { tiles: string; max_zoom: number; attribution: string };
  cms: { url: string | null; token: string | null };
  run: { trajectories: number; tracks: number };
}

export interface ProfileSummary {
  id: string;
  label: string;
  municipality: { name: string; uf: string; ibge_code: string };
  /** Data assembled automatically and not reviewed: offered only through the search, with a label. */
  experimental?: boolean;
}

/** A municipality being assembled on demand (POST /profiles/builds/{code}), polled until it is done. */
export interface BuildView {
  id: string;
  status: "queued" | "running" | "done" | "failed";
  /** What is being fetched or derived now, e.g. "Soil · ISRIC SoilGrids". */
  stage: string;
  /** Share done, 0 to 1. */
  fraction: number;
  error: string | null;
  /** Id of the profile it becomes. */
  profile: string;
}

export interface Profile extends ProfileSummary {
  initial_node: { state: string; soil: Record<string, number>; climate: { lat: number; long: number } };
  scope?: string;
  economics?: { reference_currency_month?: string; discount_rate?: unknown };
  climate_history?: { period: [string, string]; source: string };
}

/** MAPA ZARC planting windows per crop: lowest published risk (%) of each decendio 1-36; null for the
 *  project's all-year windows of covers without an official row. */
export interface PlantingWindows {
  seasons: string[];
  risk_levels: number[];
  crops: Record<string, { official: boolean; risk: Record<string, number | null> }>;
  source: { publisher: string; system: string; url: string; license?: string };
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
  /** Share of P95 against CVaR5 in the economic score (the team's slider: 0-1, default 0.5). */
  return_weight: { default: number; step: number };
  /** Evidence behind a sequence: its count of priced scenarios (data/reference/visualization-run-settings.json). */
  support: { weight: number; minimum_ranked: number; minimum_recommended: number; full_score: number };
  environment_weight: { default_weight: number; maximum_weight: number; weight_step: number };
  soil_share: number;
  water_share: number;
  /** Soil score = carbon share × carbon score + N share × total-N score (visualization-run-settings.json). */
  carbon_share_within_soil: number;
  nitrogen_share_within_soil: number;
  /** C:N target of total N, kg N/ha per g/kg of soil carbon, and the stock/target ratios bounding low and near. */
  nitrogen_target_per_carbon: number;
  nitrogen_ratio_limits: [number, number];
  soil_reference: number;
  water_scale: number;
}

export interface RunChoices {
  crops: string[];
  initial_crops: string[];
  /** Harvests of a cane field before it is reformed; null when the profile has no cane. */
  sugarcane_cuts: number | null;
  ranking: RankingSettings;
  model: ModelSettings;
}

/** The engine's own numbers, shown in "Behind your estimate". */
export interface ModelSettings {
  dirichlet_alpha: number;
  discount_rate: number;
  period_days: number;
  periods_per_year: number;
  decision_steps_per_year: number;
  horizon_years: number;
}

export type WaterClass = "water_low" | "water_medium" | "water_high";

export interface Route {
  crops: string[];
  share: number;
  trajectories: number;
  value: ValueSummary | null;
  final_carbon: number;
  final_carbon_class: "low" | "medium" | "high";
  final_water_multiplier: number;
  /** Share of the route's trajectories ending in each water class. */
  final_water: Record<WaterClass, number>;
  /** Mean final water storage, as a fraction of the soil's capacity. */
  final_water_fraction: number;
  /** Mean final total-N stock, kg N/ha (not available N). */
  final_total_nitrogen: number;
  /** Yield lost at the harvest of each planting by replanting the same crop; null when nitrogen decides it. */
  yield_penalty: number[] | null;
}

/** Fixed-bin histogram of a route's present values, with the spread the chart's smoothing uses. */
export interface Distribution {
  start: number;
  width: number;
  counts: number[];
  sd: number;
  q25: number;
  q75: number;
}

export type Policy = { kind: "markov" } | { kind: "rotation"; sequence: string[]; fallback: string };

export interface ScenarioRequest {
  id: string;
  label: string;
  initial_state?: string;
  /** Next harvest of standing cane (1 = first cut); only when the scenario starts on sugarcane. */
  initial_sugarcane_cut?: number;
  policy: Policy;
}

export interface ValueSummary {
  mean: number;
  p5: number;
  p50: number;
  p95: number;
  cvar5: number;
  count: number;
  /** Share of the valid present values below zero (a loss over the horizon). */
  loss_probability: number;
  /** Only on routes with enough priced scenarios to be recommended. */
  distribution?: Distribution;
}

/** Money scale of the ranking: CVaR5 and P95 over every priced scenario of the routes that can be ranked. */
export interface RankingReference {
  cvar5: number;
  p95: number;
  count: number;
  routes: number;
}

export interface Track {
  crop: string[];
  /** Next cut of the cane in the field; 0 when the field holds another crop or none. */
  cane_cut: number[];
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
  ranking_reference: RankingReference | null;
  tracks: Track[];
}

export interface JobView {
  id: string;
  status: "running" | "done" | "failed";
  done: number;
  total: number;
  result: RunResult | null;
  error: string | null;
}

/** One route of a finished job, beyond its summary. Class counts are [low, medium, high] per period. */
export interface RouteDetail {
  crops: string[];
  trajectories: number;
  frames: { water: number[][]; soil: number[][]; nitrogen: number[][] };
  water: Record<string, number>[];
  carbon: { p5: number; p50: number; p95: number }[];
  tracks: Pick<Track, "crop" | "cane_cut">[];
}

export interface RunResult {
  profile: string;
  seed: number;
  device: "gpu" | "cpu";
  seconds: number;
  clock: { period_days: number; periods: number; horizon_years: number };
  crops: string[];
  ranking: RankingSettings;
  model: ModelSettings;
  scenarios: ScenarioResult[];
}

export type Position = [longitude: number, latitude: number];

/** A Brazilian municipality from the IBGE list (experimental search). */
export interface Municipality {
  code: string;
  name: string;
  uf: string;
}

export interface Boundary {
  features: { geometry: { type: "Polygon"; coordinates: Position[][] } | { type: "MultiPolygon"; coordinates: Position[][][] } }[];
}
