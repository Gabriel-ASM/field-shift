/** Web Mercator in "tile units": one unit is one tile at WORLD_ZOOM. x grows east, y grows south. */

import type { Position } from "../types.ts";

export const WORLD_ZOOM = 5;

export function tileX(longitude: number, zoom: number): number {
  return ((longitude + 180) / 360) * 2 ** zoom;
}

export function tileY(latitude: number, zoom: number): number {
  const radians = (latitude * Math.PI) / 180;
  return ((1 - Math.asinh(Math.tan(radians)) / Math.PI) / 2) * 2 ** zoom;
}

/** World position of a place: [x, y] in tile units of WORLD_ZOOM. */
export function toWorld([longitude, latitude]: Position): [number, number] {
  return [tileX(longitude, WORLD_ZOOM), tileY(latitude, WORLD_ZOOM)];
}

export interface Tile {
  x: number;
  y: number;
  zoom: number;
}

/** Every tile of `zoom` touching the box between two corners. */
export function tilesCovering(northWest: Position, southEast: Position, zoom: number): Tile[] {
  const tiles: Tile[] = [];
  const [x0, x1] = [Math.floor(tileX(northWest[0], zoom)), Math.floor(tileX(southEast[0], zoom))];
  const [y0, y1] = [Math.floor(tileY(northWest[1], zoom)), Math.floor(tileY(southEast[1], zoom))];
  for (let x = x0; x <= x1; x++) for (let y = y0; y <= y1; y++) tiles.push({ x, y, zoom });
  return tiles;
}

/** Tiles of `zoom` within `radius` tiles of a place. */
export function tilesAround(place: Position, zoom: number, radius: number): Tile[] {
  const [cx, cy] = [Math.floor(tileX(place[0], zoom)), Math.floor(tileY(place[1], zoom))];
  const tiles: Tile[] = [];
  for (let x = cx - radius; x <= cx + radius; x++) for (let y = cy - radius; y <= cy + radius; y++) tiles.push({ x, y, zoom });
  return tiles;
}

/** Side of a tile in world units, and the world position of its centre. */
export function tilePlacement({ x, y, zoom }: Tile): { size: number; centre: [number, number] } {
  const size = 2 ** (WORLD_ZOOM - zoom);
  return { size, centre: [(x + 0.5) * size, (y + 0.5) * size] };
}

export function tileUrl(template: string, { x, y, zoom }: Tile): string {
  return template.replace("{z}", String(zoom)).replace("{x}", String(x)).replace("{y}", String(y));
}
