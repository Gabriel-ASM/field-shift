/** Share of each crop at a fractional period, interpolated between the per-period snapshots of a scenario. */
export function sharesAt(occupancy: Record<string, number>[], crops: string[], period: number): number[] {
  const last = occupancy.length - 1;
  const clamped = Math.min(last, Math.max(0, period));
  const before = occupancy[Math.floor(clamped)] ?? {};
  const after = occupancy[Math.ceil(clamped)] ?? before;
  const blend = clamped - Math.floor(clamped);
  return crops.map((crop) => (before[crop] ?? 0) * (1 - blend) + (after[crop] ?? 0) * blend);
}
