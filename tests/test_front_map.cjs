// Tests for field_shift/front/aoi.js: the pure geometry rules of the map area selector.
// Run: node tests/test_front_map.cjs
// The same file runs in the browser (visualizacao2.html), so these are the real rules.
const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const aoi = require("../field_shift/front/aoi.js");

const root = path.join(__dirname, "..");
const MUNICIPALITIES = {
  "ariquemes-ro": "1100023",
  "franca-sp": "3516200",
  "varginha-mg": "3170701",
};

// Build the same `boundaries` structure the page embeds (profile -> {polygons}).
function loadBoundaries() {
  const out = {};
  for (const [profile, code] of Object.entries(MUNICIPALITIES)) {
    const file = path.join(root, "data/raw/ibge", `ibge-malha-municipal-${code}.geojson`);
    const geometry = JSON.parse(fs.readFileSync(file, "utf8")).features[0].geometry;
    const polygons = geometry.type === "Polygon" ? [geometry.coordinates] : geometry.coordinates;
    out[profile] = { polygons, municipality: profile.split("-")[0], uf: profile.split("-")[1].toUpperCase(), ibge_code: code };
  }
  return out;
}

// Axis-aligned square of `ha` hectares centred on [lon, lat] (planar approximation, good enough
// to land within a fraction of a percent of the target; tests assert with a tolerance).
function squareOfArea(center, ha) {
  const sideM = Math.sqrt(ha * 10000);
  const dLat = (sideM / 2) / 111194.9;
  const dLon = dLat / Math.cos(center[1] * Math.PI / 180);
  const [x, y] = center;
  return [[x - dLon, y - dLat], [x + dLon, y - dLat], [x + dLon, y + dLat], [x - dLon, y + dLat]];
}

const boundaries = loadBoundaries();
const centerOf = profile => aoi.ringCentroid(boundaries[profile].polygons[0][0]);

// --- area -------------------------------------------------------------------------------
{
  // 0.01 deg x 0.01 deg at lat -20.5: ~1111.95 m north-south, ~1041.1 m east-west => ~115.8 ha.
  const ring = [[-47.40, -20.55], [-47.39, -20.55], [-47.39, -20.54], [-47.40, -20.54]];
  const expected = (1111.95 * 1111.95 * Math.cos(20.545 * Math.PI / 180)) / 10000;
  assert.ok(Math.abs(aoi.ringAreaHa(ring) - expected) / expected < 0.005, `area ${aoi.ringAreaHa(ring)} vs ${expected}`);
  // Closed and open rings give the same area; orientation does not matter.
  assert.equal(aoi.ringAreaHa([...ring, ring[0]]), aoi.ringAreaHa(ring));
  assert.equal(aoi.ringAreaHa([...ring].reverse()), aoi.ringAreaHa(ring));
  assert.equal(aoi.ringAreaHa([[0, 0], [1, 1]]), 0);
}

// --- validity ---------------------------------------------------------------------------
{
  const square = [[0, 0], [0.001, 0], [0.001, 0.001], [0, 0.001]];
  assert.ok(aoi.isValidRing(square));
  assert.ok(!aoi.isValidRing([[0, 0], [0.001, 0.001]]), "two points");
  assert.ok(!aoi.isValidRing([[0, 0], [0, 0], [0, 0]]), "one distinct point");
  assert.ok(!aoi.isValidRing([[0, 0], [0.001, 0.001], [0.002, 0.002]]), "collinear, zero area");
  assert.ok(!aoi.isValidRing([[0, 0], [0.001, 0.001], [0.001, 0], [0, 0.001]]), "bow tie crosses itself");
  assert.ok(!aoi.isValidRing([[0, 0], [NaN, 0], [0, 1]]), "NaN");
  assert.ok(!aoi.isValidRing([[0, 0], [200, 0], [0, 1]]), "longitude out of range");
}

// --- point in ring / centroid -----------------------------------------------------------
{
  const square = [[0, 0], [2, 0], [2, 2], [0, 2]];
  assert.ok(aoi.pointInRing([1, 1], square));
  assert.ok(!aoi.pointInRing([3, 1], square));
  assert.deepEqual(aoi.ringCentroid(square), [1, 1]);
  // Concave "U": the notch is outside, even though it is inside the bounding box.
  const u = [[0, 0], [3, 0], [3, 3], [2, 3], [2, 1], [1, 1], [1, 3], [0, 3]];
  assert.ok(!aoi.pointInRing([1.5, 2], u));
  assert.ok(aoi.pointInRing([0.5, 2], u));
}

// --- the 500 ha limit -------------------------------------------------------------------
{
  assert.equal(aoi.MAX_AOI_HA, 500);
  const franca = centerOf("franca-sp");
  const under = aoi.checkAoi(squareOfArea(franca, 480), boundaries);
  assert.equal(under.ok, true, JSON.stringify(under));
  assert.equal(under.profile, "franca-sp");
  assert.ok(under.area_ha > 470 && under.area_ha <= 500, `area ${under.area_ha}`);
  const over = aoi.checkAoi(squareOfArea(franca, 520), boundaries);
  assert.equal(over.ok, false);
  assert.equal(over.reason, aoi.REASON.TOO_LARGE);
  assert.ok(over.area_ha > 500, "area is reported even when rejected");
  // The limit is a parameter, so callers can tighten it.
  assert.equal(aoi.checkAoi(squareOfArea(franca, 480), boundaries, 100).reason, aoi.REASON.TOO_LARGE);
}

// --- which municipality ----------------------------------------------------------------
{
  for (const profile of Object.keys(MUNICIPALITIES)) {
    const result = aoi.checkAoi(squareOfArea(centerOf(profile), 50), boundaries);
    assert.equal(result.ok, true, `${profile}: ${JSON.stringify(result)}`);
    assert.equal(result.profile, profile);
  }
  // Brasilia: no municipality with data there.
  const outside = aoi.checkAoi(squareOfArea([-47.88, -15.79], 50), boundaries);
  assert.equal(outside.ok, false);
  assert.equal(outside.reason, aoi.REASON.OUTSIDE);
  // Straddling the Franca boundary: centred on one of its own vertices, so part is outside.
  const vertex = boundaries["franca-sp"].polygons[0][0][10];
  const straddle = aoi.checkAoi(squareOfArea(vertex, 100), boundaries);
  assert.equal(straddle.ok, false);
  assert.equal(straddle.reason, aoi.REASON.OUTSIDE);
  // Invalid geometry is reported before anything else.
  assert.equal(aoi.checkAoi([[0, 0], [1, 1]], boundaries).reason, aoi.REASON.INVALID);
}

// --- output Feature --------------------------------------------------------------------
{
  const ring = squareOfArea(centerOf("varginha-mg"), 80);
  const result = aoi.checkAoi(ring, boundaries);
  const feature = aoi.buildAoiFeature(ring, result, boundaries, new Date("2026-11-15T12:00:00Z"));
  assert.equal(feature.type, "Feature");
  assert.equal(feature.geometry.type, "Polygon");
  const [outer] = feature.geometry.coordinates;
  assert.equal(outer.length, ring.length + 1, "ring is closed");
  assert.deepEqual(outer[0], outer[outer.length - 1]);
  assert.equal(feature.properties.profile, "varginha-mg");
  assert.equal(feature.properties.ibge_code, "3170701");
  assert.equal(feature.properties.crs, "EPSG:4326");
  assert.equal(feature.properties.max_area_ha, 500);
  assert.equal(feature.properties.created_at, "2026-11-15T12:00:00.000Z");
  assert.ok(Math.abs(feature.properties.area_ha - 80) < 2, `area ${feature.properties.area_ha}`);
}

console.log("AOI rules: area, validity, 500 ha limit, municipality resolution and GeoJSON output verified.");
