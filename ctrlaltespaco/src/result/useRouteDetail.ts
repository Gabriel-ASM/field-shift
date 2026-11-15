import { useEffect, useState } from "react";
import { getRoute } from "../api.ts";
import type { RouteDetail } from "../types.ts";

/** Detail of the route on screen, asked from the job that simulated it; null while it loads. */
export function useRouteDetail(job: string | null, crops: string[]): { detail: RouteDetail | null; error: string | null } {
  const [state, setState] = useState<{ key: string; detail: RouteDetail | null; error: string | null }>({ key: "", detail: null, error: null });
  const key = `${job}|${crops.join(",")}`;
  useEffect(() => {
    if (!job) return;
    let current = true;
    getRoute(job, crops).then(
      (detail) => current && setState({ key, detail, error: null }),
      (failure: unknown) => current && setState({ key, detail: null, error: failure instanceof Error ? failure.message : String(failure) }),
    );
    return () => { current = false; };
    // `key` stands for job and crops.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [key]);
  return state.key === key ? state : { detail: null, error: null };
}
