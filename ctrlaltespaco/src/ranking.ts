/** The team's 0-10 ranking of crop sequences: financial return blended with final soil and water. */

import type { RankingSettings, Route } from "./types.ts";

export interface RankedRoute {
  route: Route;
  economic: number;
  soil: number;
  water: number;
  environment: number;
  total: number;
}

const clamp = (value: number, low: number, high: number) => Math.min(high, Math.max(low, value));

/** Maps a signed value to the score range: zero is break-even, `scale` reaches the ends. */
export function scoreOnTen(value: number, scale: number, settings: RankingSettings): number {
  const span = value < 0 ? settings.break_even - settings.minimum : settings.maximum - settings.break_even;
  return clamp(settings.break_even + (value / Math.max(1e-9, Math.abs(scale))) * span, settings.minimum, settings.maximum);
}

/** Routes with enough priced trajectories to be compared; all priced ones when none has enough. */
export function comparable(routes: Route[], settings: RankingSettings): Route[] {
  const priced = routes.filter((route) => route.value);
  const sampled = priced.filter((route) => route.value!.count >= settings.minimum_samples);
  return sampled.length ? sampled : priced;
}

/** One money scale for every route: the largest tail loss or high return among them. */
export function moneyScale(routes: Route[], settings: RankingSettings): number {
  const extremes = routes.flatMap((route) => [Math.abs(route.value!.cvar5), Math.abs(route.value!.p95)]);
  return Math.max(settings.minimum_scale, ...extremes);
}

function scored(route: Route, scale: number, settings: RankingSettings, weight: number): RankedRoute {
  const economic = scoreOnTen(route.value!.p50, scale, settings);
  const soil = clamp((route.final_carbon / settings.soil_reference) * settings.maximum, settings.minimum, settings.maximum);
  const water = scoreOnTen(route.final_water_multiplier - 1, settings.water_scale, settings);
  const environment = settings.soil_share * soil + settings.water_share * water;
  return { route, economic, soil, water, environment, total: (1 - weight) * economic + weight * environment };
}

/** Best sequence first. `weight` is the share of the score given to soil and water (0 to the maximum weight). */
export function rank(routes: Route[], settings: RankingSettings, weight: number): RankedRoute[] {
  const candidates = comparable(routes, settings);
  if (!candidates.length) return [];
  const scale = moneyScale(candidates, settings);
  return candidates.map((route) => scored(route, scale, settings, weight)).sort((a, b) => b.total - a.total);
}
