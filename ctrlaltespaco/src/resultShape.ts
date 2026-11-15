/** Whether a run result has the fields the result screen reads. A bundle from another build may receive a result
 *  it does not understand; that must not be reported as "no priced sequence". */

import type { RunResult } from "./types.ts";

type Loose = Record<string, unknown>;

const isObject = (value: unknown): value is Loose => typeof value === "object" && value !== null;
const VALUE_FIELDS = ["p50", "p95", "cvar5", "count"];

/** A route's present value: null when unpriced, else the summary the ranking reads. */
function wellFormedValue(value: unknown): boolean {
  return value === null || (isObject(value) && VALUE_FIELDS.every((field) => typeof value[field] === "number"));
}

function wellFormedRoute(route: unknown): boolean {
  return isObject(route) && Array.isArray(route.crops) && "value" in route && wellFormedValue(route.value);
}

/** The first scenario carries routes and a ranking reference (possibly null); the run carries the ranking settings. */
export function wellFormed(run: RunResult): boolean {
  const loose = run as unknown as Loose;
  const scenario = Array.isArray(loose.scenarios) ? (loose.scenarios[0] as unknown) : undefined;
  return isObject(loose.ranking) && isObject(loose.ranking.support) && isObject(scenario)
    && "ranking_reference" in scenario && Array.isArray(scenario.routes) && scenario.routes.every(wellFormedRoute);
}
