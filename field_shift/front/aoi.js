/*
 * aoi.js - geometry rules for the Field Shift "area of interest" (AOI) selector.
 *
 * RESPONSIBILITY
 *   Pure functions, NO DOM and NO Leaflet. Given a polygon drawn on the map it answers:
 *     1. is the geometry valid?                       (isValidRing)
 *     2. how many hectares is it?                      (ringAreaHa)
 *     3. is it within the 500 ha limit?                (MAX_AOI_HA, checkAoi)
 *     4. which municipality profile does it belong to? (resolveProfile)
 *     5. what GeoJSON do we hand to the analysis?      (buildAoiFeature)
 *   map.js is the only consumer in the browser; tests/test_front_map.cjs loads this very file
 *   with require(), so the rules that run in the page are the rules that are tested.
 *
 * CONVENTIONS (read before editing)
 *   - Coordinates are [longitude, latitude] in degrees, EPSG:4326 (GeoJSON order).
 *     Leaflet uses [lat, lng]; the conversion happens in map.js, never here.
 *   - A "ring" is an array of [lon, lat]. It may or may not repeat the first point at the end;
 *     every function here accepts both and normalises with openRing().
 *   - A municipality "polygon" is an array of rings: [outer, hole1, hole2, ...].
 *   - Areas are computed on a sphere (see ringAreaHa). The server must re-validate the limit
 *     with an equal-area projection; this client value is for feedback, not authority.
 *
 * DO NOT add anything that touches window/document here: it would break the Node tests and
 * the guarantee that the area rule is testable in isolation.
 */
(function (root, factory) {
  "use strict";
  const api = factory();
  if (typeof module === "object" && module.exports) module.exports = api;
  else root.FieldShiftAoi = api;
})(typeof self !== "undefined" ? self : this, function () {
  "use strict";

  /** Hard limit of the selectable area, in hectares. Change it here only. */
  const MAX_AOI_HA = 500;
  /** Authalic (equal-area) radius of the WGS 84 ellipsoid, metres. */
  const EARTH_AUTHALIC_RADIUS_M = 6371007.2;
  const M2_PER_HA = 10000;
  /** Rings smaller than 1 m2 are treated as degenerate (collinear or repeated points). */
  const MIN_RING_AREA_HA = 1e-4;
  const RAD = Math.PI / 180;

  /** Failure reasons returned by checkAoi(); map.js turns them into user-facing text. */
  const REASON = Object.freeze({
    INVALID: "invalid_geometry",
    TOO_LARGE: "too_large",
    OUTSIDE: "outside_coverage",
  });

  /**
   * Drop the closing point (if the ring repeats its first vertex) so loops can treat the ring
   * as a cyclic list.
   * @param {number[][]} ring [lon, lat] vertices, closed or open.
   * @returns {number[][]} open ring (a new array; the input is not modified).
   */
  function openRing(ring) {
    if (!Array.isArray(ring)) return [];
    const last = ring.length - 1;
    if (last > 0 && ring[0][0] === ring[last][0] && ring[0][1] === ring[last][1]) return ring.slice(0, last);
    return ring.slice();
  }

  /**
   * Area of a ring on a sphere of authalic radius, in hectares.
   * Uses the trapezoid-on-a-sphere formula  A = R^2/2 * |sum (l2-l1) * (2 + sin f1 + sin f2)|
   * (edges follow constant latitude/longitude steps, as drawn on a web map). The tests check
   * it against a hand-computed square within 0.5 %.
   * @param {number[][]} ring [lon, lat] vertices in degrees, closed or open.
   * @returns {number} hectares (always >= 0).
   */
  function ringAreaHa(ring) {
    const pts = openRing(ring);
    if (pts.length < 3) return 0;
    let sum = 0;
    for (let i = 0; i < pts.length; i++) {
      const [lon1, lat1] = pts[i];
      const [lon2, lat2] = pts[(i + 1) % pts.length];
      let dLon = (lon2 - lon1) * RAD;
      // Keep the longitude step in (-pi, pi] so a ring crossing the antimeridian still works.
      if (dLon > Math.PI) dLon -= 2 * Math.PI;
      else if (dLon <= -Math.PI) dLon += 2 * Math.PI;
      sum += dLon * (2 + Math.sin(lat1 * RAD) + Math.sin(lat2 * RAD));
    }
    return (Math.abs(sum) * EARTH_AUTHALIC_RADIUS_M * EARTH_AUTHALIC_RADIUS_M) / 2 / M2_PER_HA;
  }

  /**
   * Signed cross product of (b - a) x (c - a): > 0 if a->b->c turns counter-clockwise,
   * < 0 clockwise, 0 collinear.
   * @returns {number}
   */
  function orient(a, b, c) {
    return (b[0] - a[0]) * (c[1] - a[1]) - (b[1] - a[1]) * (c[0] - a[0]);
  }

  /**
   * Proper intersection of segments ab and cd (they cross at one interior point).
   * Touching at an endpoint or overlapping collinearly does NOT count as crossing.
   * @returns {boolean}
   */
  function segmentsCross(a, b, c, d) {
    const o1 = orient(a, b, c), o2 = orient(a, b, d), o3 = orient(c, d, a), o4 = orient(c, d, b);
    return o1 * o2 < 0 && o3 * o4 < 0;
  }

  /**
   * A drawn ring is valid when it has >= 3 distinct finite vertices inside lon/lat range,
   * non-zero area, and no two non-adjacent edges cross (a "bow tie" is rejected).
   * @param {number[][]} ring
   * @returns {boolean}
   */
  function isValidRing(ring) {
    const pts = openRing(ring);
    if (pts.length < 3) return false;
    for (const p of pts) {
      if (!Array.isArray(p) || p.length < 2) return false;
      const [lon, lat] = p;
      if (!Number.isFinite(lon) || !Number.isFinite(lat) || Math.abs(lon) > 180 || Math.abs(lat) > 90) return false;
    }
    if (new Set(pts.map(p => p[0] + "," + p[1])).size < 3) return false;
    // Collinear points give ~1e-9 ha through floating-point noise, not exactly 0.
    if (ringAreaHa(pts) < MIN_RING_AREA_HA) return false;
    const n = pts.length;
    for (let i = 0; i < n; i++) {
      const a = pts[i], b = pts[(i + 1) % n];
      for (let j = i + 1; j < n; j++) {
        // Adjacent edges share a vertex and cannot properly cross.
        if (j === i || (j + 1) % n === i || (i + 1) % n === j) continue;
        if (segmentsCross(a, b, pts[j], pts[(j + 1) % n])) return false;
      }
    }
    return true;
  }

  /**
   * Ray-casting point-in-ring test (even-odd rule). Points exactly on an edge may fall on
   * either side; callers needing tolerance should shrink the polygon, not this function.
   * @param {number[]} point [lon, lat]
   * @param {number[][]} ring
   * @returns {boolean}
   */
  function pointInRing(point, ring) {
    const pts = openRing(ring);
    const [x, y] = point;
    let inside = false;
    for (let i = 0, j = pts.length - 1; i < pts.length; j = i++) {
      const [xi, yi] = pts[i], [xj, yj] = pts[j];
      if (yi > y !== yj > y && x < ((xj - xi) * (y - yi)) / (yj - yi) + xi) inside = !inside;
    }
    return inside;
  }

  /**
   * Area-weighted planar centroid in lon/lat (fine at parcel/municipality scale).
   * Falls back to the vertex mean for a degenerate ring.
   * @param {number[][]} ring
   * @returns {number[]} [lon, lat]
   */
  function ringCentroid(ring) {
    const pts = openRing(ring);
    let a = 0, cx = 0, cy = 0;
    for (let i = 0; i < pts.length; i++) {
      const [x1, y1] = pts[i], [x2, y2] = pts[(i + 1) % pts.length];
      const cross = x1 * y2 - x2 * y1;
      a += cross;
      cx += (x1 + x2) * cross;
      cy += (y1 + y2) * cross;
    }
    if (Math.abs(a) < 1e-12) {
      const n = pts.length || 1;
      return [pts.reduce((s, p) => s + p[0], 0) / n, pts.reduce((s, p) => s + p[1], 0) / n];
    }
    return [cx / (3 * a), cy / (3 * a)];
  }

  /**
   * Is `ring` entirely inside `polygon` ([outer, ...holes])?
   * Requires: every vertex and the centroid inside the outer ring and outside every hole,
   * and no edge of `ring` properly crossing any edge of the polygon.
   * @param {number[][]} ring
   * @param {number[][][]} polygon
   * @returns {boolean}
   */
  function ringInsidePolygon(ring, polygon) {
    const pts = openRing(ring);
    const [outer, ...holes] = polygon;
    const probes = [...pts, ringCentroid(pts)];
    for (const p of probes) {
      if (!pointInRing(p, outer)) return false;
      if (holes.some(h => pointInRing(p, h))) return false;
    }
    for (const boundary of polygon) {
      const b = openRing(boundary);
      for (let i = 0; i < pts.length; i++) {
        const a1 = pts[i], a2 = pts[(i + 1) % pts.length];
        for (let j = 0; j < b.length; j++) if (segmentsCross(a1, a2, b[j], b[(j + 1) % b.length])) return false;
      }
    }
    return true;
  }

  /**
   * Find the municipality profile whose boundary fully contains the ring.
   * @param {number[][]} ring drawn polygon, [lon, lat].
   * @param {Object<string, {polygons: number[][][][]}>} boundaries profile id -> municipality
   *        geometry as a list of polygons (a MultiPolygon-shaped list; see generator).
   * @returns {string|null} profile id, or null when no municipality with data contains it.
   */
  function resolveProfile(ring, boundaries) {
    for (const [profile, municipality] of Object.entries(boundaries || {})) {
      if (municipality.polygons.some(polygon => ringInsidePolygon(ring, polygon))) return profile;
    }
    return null;
  }

  /**
   * Full validation used by the UI after every create/edit.
   * Order matters: geometry first, then size, then coverage, so the user sees the most
   * fundamental problem first.
   * @param {number[][]} ring
   * @param {Object} boundaries see resolveProfile().
   * @param {number} [maxHa=MAX_AOI_HA]
   * @returns {{ok: boolean, reason: (string|null), area_ha: number, profile: (string|null)}}
   *          `area_ha` is filled whenever the geometry is valid, even if the check fails.
   */
  function checkAoi(ring, boundaries, maxHa = MAX_AOI_HA) {
    if (!isValidRing(ring)) return { ok: false, reason: REASON.INVALID, area_ha: 0, profile: null };
    const area_ha = ringAreaHa(ring);
    if (area_ha > maxHa) return { ok: false, reason: REASON.TOO_LARGE, area_ha, profile: null };
    const profile = resolveProfile(ring, boundaries);
    if (profile === null) return { ok: false, reason: REASON.OUTSIDE, area_ha, profile: null };
    return { ok: true, reason: null, area_ha, profile };
  }

  /**
   * GeoJSON Feature handed to the analysis (and downloaded by the user). Contract: see
   * docs/mapa-seletor.md ("Contrato da AOI").
   * @param {number[][]} ring drawn polygon, [lon, lat], valid and already checked.
   * @param {{area_ha: number, profile: string}} result output of checkAoi() with ok === true.
   * @param {Object} boundaries see resolveProfile(); supplies municipality metadata.
   * @param {Date} [now=new Date()] injectable for tests.
   * @returns {Object} GeoJSON Feature<Polygon> with a closed ring.
   */
  function buildAoiFeature(ring, result, boundaries, now = new Date()) {
    const open = openRing(ring);
    const municipality = boundaries[result.profile];
    return {
      type: "Feature",
      geometry: { type: "Polygon", coordinates: [[...open, open[0]]] },
      properties: {
        area_ha: Math.round(result.area_ha * 100) / 100,
        max_area_ha: MAX_AOI_HA,
        profile: result.profile,
        municipality: municipality.municipality,
        uf: municipality.uf,
        ibge_code: municipality.ibge_code,
        crs: "EPSG:4326",
        area_method: "spherical, authalic radius " + EARTH_AUTHALIC_RADIUS_M + " m (client estimate)",
        created_at: now.toISOString(),
      },
    };
  }

  return {
    MAX_AOI_HA, EARTH_AUTHALIC_RADIUS_M, REASON,
    openRing, ringAreaHa, segmentsCross, isValidRing, pointInRing, ringCentroid,
    ringInsidePolygon, resolveProfile, checkAoi, buildAoiFeature,
  };
});
