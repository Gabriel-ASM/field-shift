/** Smoothed density of a route's present values, for the return distribution chart. Same rule as renderReturnChart
 *  in field_shift/front/producer.js (Gaussian kernel, Silverman-type bandwidth, 151 points, 3 bandwidths of margin),
 *  applied to the engine's fixed-bin histogram: each bin counts as its centre, weighted by its count. */

import type { Distribution } from "../types.ts";

const POINTS = 150;

export interface DensityPoint {
  value: number;
  density: number;
}

export interface Density {
  minimum: number;
  maximum: number;
  points: DensityPoint[];
}

function total(distribution: Distribution): number {
  return distribution.counts.reduce((sum, count) => sum + count, 0);
}

/** Kernel width: at least 1 BRL and 1/200 of the spread; otherwise 0.9 · min(sd, IQR/1.34) · n^(-1/5). */
export function bandwidth(distribution: Distribution): number {
  const n = total(distribution);
  const spread = distribution.width * distribution.counts.length;
  const iqr = distribution.q75 - distribution.q25;
  const scale = iqr > 0 ? Math.min(distribution.sd, iqr / 1.34) : distribution.sd;
  return Math.max(1, spread / 200, 0.9 * scale * n ** -0.2);
}

function centres(distribution: Distribution): number[] {
  return distribution.counts.map((_, index) => distribution.start + (index + 0.5) * distribution.width);
}

export function density(distribution: Distribution): Density {
  const width = bandwidth(distribution);
  const at = centres(distribution);
  const minimum = distribution.start - 3 * width;
  const maximum = distribution.start + distribution.width * distribution.counts.length + 3 * width;
  const points = Array.from({ length: POINTS + 1 }, (_, step) => {
    const value = minimum + ((maximum - minimum) * step) / POINTS;
    let sum = 0;
    at.forEach((centre, index) => {
      const z = (value - centre) / width;
      if (Math.abs(z) <= 4) sum += distribution.counts[index]! * Math.exp(-0.5 * z * z);
    });
    return { value, density: sum };
  });
  return { minimum, maximum, points };
}
