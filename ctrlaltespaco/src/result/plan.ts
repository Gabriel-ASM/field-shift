/** The printable plan's calendar: plantings read off a trajectory, and ZARC windows in words. */

import type { StripTrack } from "../ui/tracks.ts";
import { segments } from "../ui/tracks.ts";

const MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];
const MONTH_DAYS = [31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31];
const PART = ["early", "mid", "late"];

/** Decendio (1-36) of a day of the year counted from January 1st, as the engine's calendar. */
export function decendioOfDay(day: number): number {
  let remaining = Math.floor(day) % 365;
  for (let month = 0; month < 12; month++) {
    if (remaining < MONTH_DAYS[month]!) return month * 3 + Math.min(Math.floor(remaining / 10), 2) + 1;
    remaining -= MONTH_DAYS[month]!;
  }
  return 36;
}

export const decendioName = (decendio: number) => `${PART[(decendio - 1) % 3]} ${MONTHS[Math.floor((decendio - 1) / 3)]}`;

/** One planting of the plan: the crop, its year (1-based) and the decendio it goes in. */
export interface Planting {
  crop: string;
  year: number;
  decendio: number;
}

/** Plantings along a trajectory: every stretch that starts a crop (a new cane field starts at cut 1). The crop in
 *  the field at the start is already planted, so it is not one. Day 0 is January 1st. */
export function plantings(track: StripTrack, periodsPerYear: number): Planting[] {
  const periodDays = 365 / periodsPerYear;
  return segments(track)
    .filter((segment) => segment.start > 0 && segment.crop !== "fallow" && segment.cut <= 1)
    .map((segment) => ({
      crop: segment.crop,
      year: Math.floor(segment.start / periodsPerYear) + 1,
      decendio: decendioOfDay(segment.start * periodDays),
    }));
}

/** Runs of consecutive decendios with the same risk, wrapping from late Dec to early Jan, in words. */
export function windowText(risk: Record<string, number | null>): string {
  const days = Object.keys(risk).map(Number).sort((a, b) => a - b);
  if (!days.length) return "no published window";
  if (days.length === 36 && days.every((day) => risk[day] === risk[1])) return risk[1] === null ? "all year (project assumption)" : `all year (${risk[1]}% risk)`;
  const runs: { from: number; to: number; risk: number | null }[] = [];
  for (const day of days) {
    const last = runs[runs.length - 1];
    if (last && last.to === day - 1 && last.risk === risk[day]) last.to = day;
    else runs.push({ from: day, to: day, risk: risk[day] ?? null });
  }
  const first = runs[0]!, last = runs[runs.length - 1]!;
  if (runs.length > 1 && first.from === 1 && last.to === 36 && first.risk === last.risk) {
    last.to = first.to;
    runs.shift();
  }
  return runs.map((run) => {
    const span = run.from === run.to ? decendioName(run.from) : `${decendioName(run.from)} – ${decendioName(run.to)}`;
    return run.risk === null ? span : `${span} (${run.risk}%)`;
  }).join(", ");
}
