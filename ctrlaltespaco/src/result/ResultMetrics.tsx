/** The three cards beside the sequence: income, final soil, final water (showFarmerResult in producer.js). */

import type { Route, RankingSettings, WaterClass } from "../types.ts";
import { count, money, percent } from "../ui/format.ts";

const SOIL = { low: "Needs care", medium: "Fair", high: "Good" } as const;
const WATER: Record<WaterClass, string> = { water_low: "Low", water_medium: "Medium", water_high: "High" };

/** The most frequent final water class of the route, and its share. */
export function mostFrequentWater(route: Route): [WaterClass, number] {
  const entries = Object.entries(route.final_water) as [WaterClass, number][];
  return entries.reduce((best, entry) => (entry[1] > best[1] ? entry : best), entries[0]!);
}

export function ResultMetrics({ route, settings }: { route: Route; settings: RankingSettings }) {
  const value = route.value!;
  const [water, share] = mostFrequentWater(route);
  const small = value.count < settings.support.full_score ? " · small sample" : "";
  return (
    <div className="result-metrics">
      <article className="metric-card income">
        <span className="metric-label">Estimated net income</span>
        <strong className="metric-value">{money(value.p50)} <small>/ha</small></strong>
        <span className="metric-detail">Median present value over five years · {count(value.count)} {value.count === 1 ? "scenario" : "scenarios"} with complete calculations{small}.</span>
      </article>
      <article className="metric-card">
        <span className="metric-label">Final soil condition</span>
        <strong className="metric-value">{SOIL[route.final_carbon_class]}</strong>
        <span className="metric-detail">{route.final_carbon.toFixed(1)} g/kg of estimated organic carbon at the end of the cycle.</span>
      </article>
      <article className="metric-card">
        <span className="metric-label">Available water</span>
        <strong className="metric-value">{WATER[water]}</strong>
        <span className="metric-detail">Most frequent final condition, seen in {percent(share)} of trajectories. Mean final water: {percent(route.final_water_fraction)} of capacity.</span>
      </article>
    </div>
  );
}
