import { useEffect, useState } from "react";
import { getRoute } from "../api.ts";
import type { RouteDetail } from "../types.ts";

/** Where the detail of the sequence on screen lives: a route of the chain run, or a whole refined scenario. */
export interface DetailSource {
  job: string | null;
  crops: string[] | null;
  scenario: number;
}

/** Detail of the sequence on screen; null while it loads. */
export function useRouteDetail(source: DetailSource): { detail: RouteDetail | null; error: string | null } {
  const [state, setState] = useState<{ key: string; detail: RouteDetail | null; error: string | null }>({ key: "", detail: null, error: null });
  const key = `${source.job}|${source.scenario}|${source.crops?.join(",") ?? "*"}`;
  useEffect(() => {
    if (!source.job) return;
    let current = true;
    getRoute(source.job, source.crops, source.scenario).then(
      (detail) => current && setState({ key, detail, error: null }),
      (failure: unknown) => current && setState({ key, detail: null, error: failure instanceof Error ? failure.message : String(failure) }),
    );
    return () => { current = false; };
    // `key` stands for the source.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [key]);
  return state.key === key ? state : { detail: null, error: null };
}
