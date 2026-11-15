/** The team's 0-10 ranking of crop sequences (field_shift/front/analysis.js, renderEconomicOptimization):
 *    E = α·P95 + (1−α)·CVaR5 → E10
 *    J = (1−w)[(1−λ)E10 + λ(⅔S10 + ⅓W10)] + w·A10
 *  α weighs high returns against protection in bad futures, λ is the farmer's preference for soil and water,
 *  w the fixed share of sample support A. */

import type { RankingReference, RankingSettings, Route } from "./types.ts";

export interface RankedRoute {
  route: Route;
  economic: number;
  soil: number;
  water: number;
  environment: number;
  support: number;
  total: number;
}

export interface Weights {
  economic: number;
  environment: number;
  support: number;
}

const clamp = (value: number, low: number, high: number) => Math.min(high, Math.max(low, value));

/** Maps a signed value to the score range: zero is break-even, `scale` reaches the ends. */
export function scoreOnTen(value: number, scale: number, settings: RankingSettings): number {
  const span = value < 0 ? settings.break_even - settings.minimum : settings.maximum - settings.break_even;
  return clamp(settings.break_even + (value / Math.max(1e-9, Math.abs(scale))) * span, settings.minimum, settings.maximum);
}

/** Support rises linearly with the priced scenarios of a sequence, up to the maximum at `full_score`. */
export function supportScore(count: number, settings: RankingSettings): number {
  return settings.maximum * clamp(count / settings.support.full_score, 0, 1);
}

/** Support keeps its fixed share; the farmer's preference splits the rest between economics and environment. */
export function weights(environmentPreference: number, settings: RankingSettings): Weights {
  const support = settings.support.weight;
  const environment = (1 - support) * environmentPreference;
  return { support, environment, economic: 1 - support - environment };
}

/** Routes with a priced present value from at least `minimum_ranked` scenarios. */
export function comparable(routes: Route[], settings: RankingSettings): Route[] {
  return routes.filter((route) => route.value && route.value.count >= settings.support.minimum_ranked);
}

/** One money scale for every route: CVaR5 and P95 of all ranked scenarios pooled (referenceCvar5, referenceP95). */
export function moneyScale(reference: RankingReference, settings: RankingSettings): number {
  return Math.max(Math.abs(reference.cvar5), Math.abs(reference.p95), settings.minimum_scale);
}

/** E before scaling: α of the high return (P95), the rest of the mean of the worst 5% (CVaR5). */
export function preference(route: Route, returnWeight: number): number {
  return returnWeight * route.value!.p95 + (1 - returnWeight) * route.value!.cvar5;
}

/** Total-N stock against the C:N target for the route's final carbon (nitrogenScoreOnTen of analysis.js). */
export function nitrogenScore(route: Route, settings: RankingSettings): number {
  const target = settings.nitrogen_target_per_carbon * route.final_carbon;
  return target > 0 ? clamp((route.final_total_nitrogen / target) * settings.maximum, settings.minimum, settings.maximum) : 0;
}

/** below / near / above the C:N target (soilNitrogenClass). */
export function nitrogenClass(route: Route, settings: RankingSettings): "low" | "medium" | "high" {
  const target = settings.nitrogen_target_per_carbon * route.final_carbon;
  const ratio = target > 0 ? route.final_total_nitrogen / target : 0;
  const [low, near] = settings.nitrogen_ratio_limits;
  return ratio < low ? "low" : ratio < near ? "medium" : "high";
}

function scored(route: Route, scale: number, settings: RankingSettings, share: Weights, returnWeight: number): RankedRoute {
  const economic = scoreOnTen(preference(route, returnWeight), scale, settings);
  const carbon = clamp((route.final_carbon / settings.soil_reference) * settings.maximum, settings.minimum, settings.maximum);
  const soil = settings.carbon_share_within_soil * carbon + settings.nitrogen_share_within_soil * nitrogenScore(route, settings);
  const water = scoreOnTen(route.final_water_multiplier - 1, settings.water_scale, settings);
  const environment = settings.soil_share * soil + settings.water_share * water;
  const support = supportScore(route.value!.count, settings);
  const total = share.economic * economic + share.environment * environment + share.support * support;
  return { route, economic, soil, water, environment, support, total };
}

function better(a: RankedRoute, b: RankedRoute): number {
  return b.total - a.total || b.route.value!.p50 - a.route.value!.p50 || a.route.crops.join().localeCompare(b.route.crops.join());
}

/** The farmer's two choices: λ for soil and water (0 to the maximum weight), α for P95 against CVaR5 (0 to 1). */
export interface Priorities {
  weight: number;
  returnWeight: number;
}

/** Best sequence first. */
export function rank(routes: Route[], reference: RankingReference | null, settings: RankingSettings, priorities: Priorities): RankedRoute[] {
  const candidates = comparable(routes, settings);
  if (!candidates.length || !reference) return [];
  const scale = moneyScale(reference, settings);
  const share = weights(priorities.weight, settings);
  return candidates.map((route) => scored(route, scale, settings, share, priorities.returnWeight)).sort(better);
}

/** The recommendation: the best-ranked sequence with at least `minimum_recommended` priced scenarios. */
export function recommended(ranked: RankedRoute[], settings: RankingSettings): RankedRoute | undefined {
  return ranked.find(({ route }) => route.value!.count >= settings.support.minimum_recommended);
}

/** Too few priced scenarios to be recommended; shown only as exploratory. */
export function exploratory(ranked: RankedRoute, settings: RankingSettings): boolean {
  return ranked.route.value!.count < settings.support.minimum_recommended;
}

/** Key of a route, stable across re-rankings. */
export const routeKey = (route: Route) => route.crops.join(",");

/** The sequence the result view shows: the chosen one if it can be recommended, else the recommendation. */
export function selectRoute(ranked: RankedRoute[], settings: RankingSettings, key: string | null): RankedRoute | undefined {
  const chosen = key === null ? undefined : ranked.find((item) => routeKey(item.route) === key && !exploratory(item, settings));
  return chosen ?? recommended(ranked, settings);
}

/** The options the farmer can switch between: every sequence that could be recommended, best first. */
export function options(ranked: RankedRoute[], settings: RankingSettings, limit: number): RankedRoute[] {
  return ranked.filter((item) => !exploratory(item, settings)).slice(0, limit);
}
