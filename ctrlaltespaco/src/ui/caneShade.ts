/** Shade of a cane cell in the trajectory strips: the cane colour, darker at each later cut. */

import { cropColor } from "./colors.ts";

const DARKEST = 0.55;   // share of black mixed in at the last cut

function hex(value: number): string {
  return Math.round(value).toString(16).padStart(2, "0");
}

/** `cut` 1 is the cane colour itself; `cuts` (the last cut before reform) is the darkest. */
export function caneShade(cut: number, cuts: number): string {
  const base = cropColor("sugarcane");
  const depth = cuts > 1 ? (DARKEST * (Math.min(cut, cuts) - 1)) / (cuts - 1) : 0;
  const channel = (offset: number) => hex(parseInt(base.slice(offset, offset + 2), 16) * (1 - depth));
  return `#${channel(1)}${channel(3)}${channel(5)}`;
}
