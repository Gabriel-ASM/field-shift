/** Grouping of simulated trajectories for the strips: identical timelines together, consecutive periods merged. */

import type { Track } from "../types.ts";

export type StripTrack = Pick<Track, "crop" | "cane_cut">;

/** Scenarios that unfolded the same way (same crop and cane cut in every period), with how many there are. */
export interface Group {
  track: StripTrack;
  count: number;
}

const keyOf = (track: StripTrack) => track.crop.map((crop, step) => `${crop}:${track.cane_cut[step] ?? 0}`).join("|");

export function groupTracks(tracks: StripTrack[]): Group[] {
  const groups = new Map<string, Group>();
  for (const track of tracks) {
    const key = keyOf(track);
    const group = groups.get(key);
    if (group) group.count += 1;
    else groups.set(key, { track, count: 1 });
  }
  return [...groups.values()].sort((a, b) => b.count - a.count);
}

/** One stretch of a strip: the same crop (and cane cut) from `start` to `end` (exclusive), in periods. */
export interface Segment {
  crop: string;
  cut: number;
  start: number;
  end: number;
}

export function segments(track: StripTrack): Segment[] {
  const out: Segment[] = [];
  track.crop.forEach((crop, step) => {
    const cut = track.cane_cut[step] ?? 0;
    const last = out[out.length - 1];
    if (last && last.crop === crop && last.cut === cut) last.end = step + 1;
    else out.push({ crop, cut, start: step, end: step + 1 });
  });
  return out;
}
