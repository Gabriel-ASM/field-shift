/*
 * map.js - Leaflet area selector for step 1 of the Field Shift journey (docs/visualizacao2.html).
 *
 * RESPONSIBILITY
 *   Draws the satellite map, lets the user draw ONE polygon/rectangle of at most 500 ha, shows
 *   the area live, and - when the shape is valid and inside a municipality with data - selects
 *   that municipality's profile so the existing journey continues unchanged.
 *   All geometry rules (area, 500 ha limit, which municipality) live in aoi.js; this file only
 *   wires them to Leaflet and the DOM.
 *
 * HOW IT TALKS TO THE REST OF THE PAGE (read before changing)
 *   - producer.js (the journey) is NOT modified. To select a municipality we click the matching
 *     `.city-option[data-profile=...]` button, which runs producer.js' own selectCity().
 *     `state.selecting` marks those programmatic clicks.
 *   - The same buttons are turned into "zoom to this municipality" shortcuts for the user: a
 *     capture-phase listener on their container swallows real clicks. Without a drawn area the
 *     journey cannot continue (the Continue button stays disabled).
 *   - Output: a GeoJSON Feature (see aoi.js buildAoiFeature and docs/mapa-seletor.md), available as
 *     `FieldShiftMap.getAoi()`, as the `fieldshift:aoi` event on `document` (detail = Feature, or
 *     null when cleared) and as a download.
 *
 * FALLBACK
 *   If Leaflet / Leaflet.draw did not load (no internet) or anything throws during setup, the
 *   container stays hidden and the classic SVG map keeps working exactly like the classic page.
 *
 * EXTENDING
 *   - More basemaps / layers: add entries to BASEMAPS (a layer switcher appears automatically
 *     with more than one). Check the provider's terms of use first (see docs/mapa-seletor.md).
 *   - Changing the limit: MAX_AOI_HA in aoi.js (and the server-side check when it exists).
 */
(function () {
  "use strict";

  const Aoi = window.FieldShiftAoi;
  const $ = id => document.getElementById(id);
  const container = $("aoi-map");
  if (!container) return;

  // ---- configuration -------------------------------------------------------------------
  /** Basemaps. Only Esri World Imagery for now: free to display with attribution, no API key. */
  const BASEMAPS = [
    {
      id: "esri-imagery",
      name: "Satellite (Esri)",
      url: "https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}",
      options: {
        maxNativeZoom: 19, maxZoom: 20,
        attribution: "Tiles &copy; Esri &mdash; Source: Esri, Maxar, Earthstar Geographics, and the GIS User Community",
      },
    },
  ];
  const BRAZIL_BOUNDS = [[-33.8, -73.9], [5.3, -34.8]];
  const VALID_STYLE = { color: "#5cc48a", weight: 3, fillColor: "#5cc48a", fillOpacity: 0.28, dashArray: null };
  const REJECTED_STYLE = { color: "#e0503c", weight: 3, fillColor: "#e0503c", fillOpacity: 0.25, dashArray: "6 4" };
  const BOUNDARY_STYLE = { color: "#f4f7c2", weight: 2, dashArray: "6 5", fill: true, fillOpacity: 0.05, interactive: false };

  // ---- fallback guard --------------------------------------------------------------------
  if (!window.L || !L.Control || !L.Control.Draw || !Aoi) {
    console.warn("Field Shift map: Leaflet/Leaflet.draw unavailable; keeping the classic SVG map.");
    return;
  }

  const card = container.closest(".map-card");
  const boundaries = JSON.parse($("municipal-boundaries").textContent);
  const state = { layer: null, aoi: null, lastLatLngs: null, drawing: false, tool: null, selecting: false };
  const limit = Aoi.MAX_AOI_HA;

  // ---- small helpers ---------------------------------------------------------------------
  const fmtHa = ha => ha.toLocaleString("en-US", { maximumFractionDigits: ha < 10 ? 2 : 1 });
  const toRing = latlngs => latlngs.map(p => [p.lng, p.lat]); // Leaflet [lat,lng] -> GeoJSON [lon,lat]
  const outerLatLngs = layer => { const l = layer.getLatLngs(); return Array.isArray(l[0]) ? l[0] : l; };
  const ringOf = layer => toRing(outerLatLngs(layer));
  const copyLatLngs = nested => nested.map(ring => ring.map(p => L.latLng(p.lat, p.lng)));
  const boundsRing = (a, b) => [[a.lng, a.lat], [b.lng, a.lat], [b.lng, b.lat], [a.lng, b.lat]];

  const MESSAGES = {
    [Aoi.REASON.TOO_LARGE]: r => `That area is ${fmtHa(r.area_ha)} ha. The limit is ${limit} ha: draw a smaller one.`,
    [Aoi.REASON.OUTSIDE]: () => "This area must sit entirely inside Ariquemes, Franca or Varginha, the municipalities with data.",
    [Aoi.REASON.INVALID]: () => "That shape is not valid (edges cannot cross). Try again.",
  };

  // ---- side panel (built here so the classic page carries none of it) ---------------------
  const panel = document.createElement("div");
  panel.className = "aoi-panel";
  panel.innerHTML =
    `<div class="aoi-limit">Draw your field on the map, up to <strong>${limit} ha</strong>, inside one of the municipalities with data.</div>` +
    `<div class="aoi-area" id="aoi-area">&mdash; <small>ha</small></div>` +
    `<div class="aoi-meter" id="aoi-meter"><i></i></div>` +
    `<p class="aoi-message" id="aoi-message" role="status" aria-live="polite"></p>` +
    `<button class="aoi-download" id="aoi-download" type="button" hidden>Download area (GeoJSON)</button>`;
  const note = $("city-selection-note");
  note.parentNode.insertBefore(panel, note);
  const areaEl = $("aoi-area"), meterEl = $("aoi-meter"), messageEl = $("aoi-message"), downloadEl = $("aoi-download");

  // The area figure and the message are updated separately on purpose: Leaflet.draw fires DRAWSTOP
  // right AFTER the created event, and that must not erase the message set for the new shape.
  function renderArea(areaHa) {
    areaEl.innerHTML = areaHa == null ? "&mdash; <small>ha</small>" : `${fmtHa(areaHa)} <small>ha of ${limit}</small>`;
    meterEl.firstElementChild.style.width = areaHa == null ? "0%" : `${Math.min(100, (areaHa / limit) * 100)}%`;
    meterEl.classList.toggle("is-over", areaHa != null && areaHa > limit);
  }
  function setMessage(message, kind) {
    messageEl.textContent = message || "";
    messageEl.className = "aoi-message" + (kind ? ` is-${kind}` : "");
    downloadEl.hidden = !state.aoi;
  }
  const acceptedArea = () => (state.aoi ? state.aoi.properties.area_ha : null);

  // ---- map ----------------------------------------------------------------------------------
  let map;
  try {
    container.hidden = false;
    map = L.map(container, { zoomControl: true, attributionControl: true });
    map.fitBounds(BRAZIL_BOUNDS);
    const layers = BASEMAPS.map(b => ({ ...b, layer: L.tileLayer(b.url, b.options) }));
    layers[0].layer.addTo(map);
    if (layers.length > 1) {
      L.control.layers(Object.fromEntries(layers.map(b => [b.name, b.layer])), null, { position: "topright" }).addTo(map);
    }
    L.control.scale({ imperial: false, position: "bottomright" }).addTo(map);
    if (window.ResizeObserver) new ResizeObserver(() => map.invalidateSize()).observe(container);
  } catch (error) {
    console.error("Field Shift map: initialisation failed; keeping the classic SVG map.", error);
    container.hidden = true;
    return;
  }
  card.classList.add("has-leaflet");

  // Municipality outlines + clickable labels (zoom shortcuts).
  const boundaryLayers = {};
  for (const [profile, municipality] of Object.entries(boundaries)) {
    const rings = municipality.polygons.map(polygon => polygon.map(ring => ring.map(([lon, lat]) => [lat, lon])));
    const outline = L.polygon(rings, BOUNDARY_STYLE).addTo(map);
    boundaryLayers[profile] = outline;
    const [lon, lat] = Aoi.ringCentroid(municipality.polygons[0][0]);
    L.circleMarker([lat, lon], { radius: 5, color: "#fff", weight: 2, fillColor: "#5cc48a", fillOpacity: 1 })
      .bindTooltip(`${municipality.municipality}, ${municipality.uf}`, { permanent: true, direction: "top", offset: [0, -4], className: "aoi-label" })
      .on("click", () => { if (!state.drawing) zoomTo(profile); })
      .addTo(map);
  }
  function zoomTo(profile) {
    map.fitBounds(boundaryLayers[profile].getBounds(), { padding: [24, 24], maxZoom: 13 });
  }

  // On-map live readout (shown only while drawing/editing).
  const LiveStatus = L.Control.extend({
    options: { position: "bottomleft" },
    onAdd() {
      this._el = L.DomUtil.create("div", "aoi-status");
      this._el.hidden = true;
      return this._el;
    },
    show(text, over) { this._el.hidden = false; this._el.textContent = text; this._el.classList.toggle("is-over", !!over); },
    hide() { this._el.hidden = true; },
  });
  const live = new LiveStatus().addTo(map);
  function showLive(ring) {
    if (ring.length < 3) return;
    const ha = Aoi.ringAreaHa(ring);
    live.show(`${fmtHa(ha)} ha${ha > limit ? ` · over the ${limit} ha limit` : ` of ${limit}`}`, ha > limit);
    renderArea(ha);
  }

  // ---- drawing ---------------------------------------------------------------------------------
  const drawn = new L.FeatureGroup().addTo(map);
  const shape = { allowIntersection: false, showArea: false, shapeOptions: VALID_STYLE, drawError: { color: "#e0503c", message: "Edges cannot cross." } };
  try {
    // Friendly toolbar labels (L.drawLocal ships with Leaflet.draw).
    L.drawLocal.draw.toolbar.buttons.polygon = `Draw a polygon (max ${limit} ha)`;
    L.drawLocal.draw.toolbar.buttons.rectangle = `Draw a rectangle (max ${limit} ha)`;
  } catch (_) { /* cosmetic only */ }
  // showArea stays false on purpose: Leaflet.draw 1.0.4's own area label throws a ReferenceError in
  // strict mode. The area is computed by aoi.js instead (consistent with the limit check).
  map.addControl(new L.Control.Draw({
    position: "topleft",
    draw: { polygon: shape, rectangle: { showArea: false, shapeOptions: VALID_STYLE },
            polyline: false, circle: false, marker: false, circlemarker: false },
    edit: { featureGroup: drawn },
  }));

  function accept(layer, ring, result) {
    state.layer = layer;
    state.lastLatLngs = copyLatLngs(layer.getLatLngs());
    layer.setStyle(VALID_STYLE);
    state.aoi = Aoi.buildAoiFeature(ring, result, boundaries);
    const properties = state.aoi.properties;
    // Reuse producer.js: clicking the profile button runs its selectCity() (enables Continue, fills texts).
    state.selecting = true;
    try { document.querySelector(`.city-option[data-profile="${result.profile}"]`).click(); } finally { state.selecting = false; }
    note.append(document.createElement("br"), document.createTextNode(`Area drawn: ${fmtHa(result.area_ha)} ha.`));
    document.querySelectorAll("[data-selected-city]").forEach(node => {
      node.textContent = `${properties.municipality} · ${properties.uf} · ${fmtHa(result.area_ha)} ha`;
    });
    live.hide();
    renderArea(result.area_ha);
    setMessage(`Area accepted, inside ${properties.municipality}, ${properties.uf}.`, "ok");
    document.dispatchEvent(new CustomEvent("fieldshift:aoi", { detail: state.aoi }));
  }

  function clearSelection() {
    state.layer = null; state.aoi = null; state.lastLatLngs = null;
    document.querySelectorAll("[data-profile]").forEach(node => {
      node.classList.remove("is-selected");
      node.setAttribute("aria-pressed", "false");
    });
    $("location-next").disabled = true;
    note.textContent = "Draw an area to continue.";
    live.hide();
    renderArea(null);
    setMessage("", null);
    document.dispatchEvent(new CustomEvent("fieldshift:aoi", { detail: null }));
  }

  /** Rejected shapes are shown in red for a moment, then removed; any previous valid area is kept. */
  function reject(layer, result, keptPrevious) {
    if (layer && !map.hasLayer(layer)) {
      layer.setStyle(REJECTED_STYLE);
      layer.addTo(map);
      setTimeout(() => map.removeLayer(layer), 2200);
    }
    live.hide();
    renderArea(result.area_ha || acceptedArea());
    setMessage(MESSAGES[result.reason](result) + (keptPrevious ? " Your previous area was kept." : ""), "error");
  }

  map.on(L.Draw.Event.DRAWSTART, e => { state.drawing = true; state.tool = e.layerType; setMessage("", null); });
  // Fired after CREATED too: only reset flags and the area figure, never the message.
  map.on(L.Draw.Event.DRAWSTOP, () => { state.drawing = false; state.tool = null; rectStart = null; live.hide(); renderArea(acceptedArea()); });
  map.on(L.Draw.Event.DRAWVERTEX, e => showLive(toRing(e.layers.getLayers().map(m => m.getLatLng()))));

  // Rectangles have no "vertex" event: follow the mouse from the first press (live area while dragging).
  let rectStart = null;
  map.on("mousedown", e => { if (state.drawing && state.tool === "rectangle") rectStart = e.latlng; });
  map.on("mousemove", e => { if (rectStart) showLive(boundsRing(rectStart, e.latlng)); });
  map.on("mouseup", () => { rectStart = null; });

  map.on(L.Draw.Event.CREATED, e => {
    const ring = ringOf(e.layer);
    const result = Aoi.checkAoi(ring, boundaries);
    if (!result.ok) { reject(e.layer, result, !!state.aoi); return; }
    drawn.clearLayers(); // exactly one active area
    drawn.addLayer(e.layer);
    accept(e.layer, ring, result);
  });

  // While vertices are dragged / the rectangle is resized.
  map.on(L.Draw.Event.EDITVERTEX, e => showLive(ringOf(e.poly)));
  map.on("draw:editresize", e => showLive(ringOf(e.layer)));

  map.on(L.Draw.Event.EDITED, () => {
    if (!state.layer) return;
    const ring = ringOf(state.layer);
    const result = Aoi.checkAoi(ring, boundaries);
    if (!result.ok) {
      state.layer.setLatLngs(state.lastLatLngs); // revert to the last valid geometry
      reject(null, result, true);
      return;
    }
    accept(state.layer, ring, result);
  });
  map.on(L.Draw.Event.DELETED, () => { if (!drawn.getLayers().length) clearSelection(); });

  // ---- journey integration ----------------------------------------------------------------------
  // Municipality buttons only zoom (capture phase on the parent: producer.js' own listener never runs).
  document.querySelector(".city-options").addEventListener("click", event => {
    const button = event.target.closest(".city-option");
    if (!button || state.selecting) return;
    event.stopPropagation();
    zoomTo(button.dataset.profile);
  }, true);

  const heading = document.querySelector("#screen-location .screen-heading p");
  if (heading) heading.textContent = `Draw your field on the satellite map, up to ${limit} ha, inside one of the municipalities with data. We'll use that municipality's climate, soil, and most common crops.`;
  const panelTitle = document.querySelector(".choice-panel h3");
  if (panelTitle) panelTitle.textContent = "Draw your area";
  const panelText = document.querySelector(".choice-panel > p");
  if (panelText) panelText.textContent = "Use the polygon or rectangle tool on the map. These buttons zoom to each municipality with data.";
  $("location-next").disabled = true;
  note.textContent = "Draw an area to continue.";
  renderArea(null);
  setMessage("", null);

  downloadEl.addEventListener("click", () => {
    if (!state.aoi) return;
    const { profile, area_ha } = state.aoi.properties;
    const url = URL.createObjectURL(new Blob([JSON.stringify(state.aoi, null, 2)], { type: "application/geo+json" }));
    const link = document.createElement("a");
    link.href = url;
    link.download = `field-shift-aoi-${profile}-${Math.round(area_ha)}ha.geojson`;
    document.body.appendChild(link);
    link.click();
    link.remove();
    // Revoke late: some browsers read the blob asynchronously after the click.
    setTimeout(() => URL.revokeObjectURL(url), 30000);
  });

  /** Small public surface for debugging, tests and the future analysis hook-up. */
  window.FieldShiftMap = { map, getAoi: () => state.aoi, maxAreaHa: limit };
})();
