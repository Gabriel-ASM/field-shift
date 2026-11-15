/** Geometry for the experimental municipality search: where a boundary is, and the nearest complete profile. */

import type { Boundary, Profile } from "../types.ts";

const EARTH_KM = 6371;

/** Every [longitude, latitude] of a boundary's rings. */
function points(boundary: Boundary): number[][] {
  return boundary.features.flatMap(({ geometry }) =>
    geometry.type === "Polygon" ? geometry.coordinates.flat() : geometry.coordinates.flat(2));
}

/** Centre of the boundary's bounding box, as [latitude, longitude]. */
export function centre(boundary: Boundary): [number, number] {
  const all = points(boundary);
  const lon = all.map((point) => point[0]!), lat = all.map((point) => point[1]!);
  return [(Math.min(...lat) + Math.max(...lat)) / 2, (Math.min(...lon) + Math.max(...lon)) / 2];
}

/** Great-circle distance in km between two [latitude, longitude] points. */
export function distanceKm([lat1, lon1]: [number, number], [lat2, lon2]: [number, number]): number {
  const rad = Math.PI / 180;
  const a = Math.sin(((lat2 - lat1) * rad) / 2) ** 2
    + Math.cos(lat1 * rad) * Math.cos(lat2 * rad) * Math.sin(((lon2 - lon1) * rad) / 2) ** 2;
  return 2 * EARTH_KM * Math.asin(Math.sqrt(a));
}

/** The complete profile closest to a point, with its distance. */
export function nearest(profiles: Profile[], point: [number, number]): { profile: Profile; km: number } | null {
  return profiles
    .map((profile) => ({ profile, km: distanceKm(point, [profile.initial_node.climate.lat, profile.initial_node.climate.long]) }))
    .sort((a, b) => a.km - b.km)[0] ?? null;
}
