import { useSyncExternalStore } from "react";
import { playhead } from "./playhead.ts";

/** Playhead position rounded down to whole periods, so React re-renders once per period, not per frame. */
export function usePeriod(): number {
  return useSyncExternalStore(playhead.subscribe, () => Math.floor(playhead.period));
}

export function usePlaying(): boolean {
  return useSyncExternalStore(playhead.subscribe, () => playhead.playing);
}
