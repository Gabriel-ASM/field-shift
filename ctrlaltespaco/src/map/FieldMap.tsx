import L from "leaflet";
import "leaflet/dist/leaflet.css";
import "leaflet-draw/dist/leaflet.draw.css";
import { useEffect, useRef } from "react";
import type { Boundary, Profile, RuntimeConfig } from "../types.ts";

const BRAZIL: L.LatLngBoundsExpression = [[-34, -74], [5.5, -34]];
const PLACE_ZOOM = 9;
const MAX_ZOOM = 13;
const SQUARE_METRES_PER_HECTARE = 10_000;

interface FieldMapProps {
  config: RuntimeConfig;
  states: Boundary;
  profiles: Profile[];
  selected: Profile | null;
  municipality: Boundary | null;
  /** A municipality found in the experimental search, without a complete profile. */
  explored: Boundary | null;
  onSelect: (id: string) => void;
  /** Area of the field the farmer drew, in hectares; null when it is removed. */
  onArea: (hectares: number | null) => void;
}

const position = (profile: Profile): L.LatLngTuple => [profile.initial_node.climate.lat, profile.initial_node.climate.long];

function baseLayer(config: RuntimeConfig): L.TileLayer {
  const { tiles, max_zoom, attribution } = config.basemap;
  return L.tileLayer(tiles, { maxNativeZoom: max_zoom, maxZoom: MAX_ZOOM, attribution: `${attribution} · Boundaries: IBGE` });
}

function hectares(layer: L.Polygon): number {
  const ring = layer.getLatLngs()[0] as L.LatLng[];
  return L.GeometryUtil.geodesicArea(ring) / SQUARE_METRES_PER_HECTARE;
}

/** Adds the polygon tool. leaflet-draw is a classic script that expects a global `L`, so it is loaded after one exists. */
async function addDrawing(map: L.Map, onArea: (hectares: number | null) => void): Promise<void> {
  (window as unknown as { L: typeof L }).L = L;
  await import("leaflet-draw");
  const drawn = new L.FeatureGroup().addTo(map);
  const shapes = { polygon: { showArea: true }, polyline: false, rectangle: false, circle: false, marker: false, circlemarker: false } as const;
  map.addControl(new L.Control.Draw({ position: "topleft", draw: shapes, edit: { featureGroup: drawn } }));
  const report = () => {
    const [field] = drawn.getLayers() as L.Polygon[];
    onArea(field ? hectares(field) : null);
  };
  map.on(L.Draw.Event.CREATED, (event) => {
    drawn.clearLayers();
    drawn.addLayer(event.layer);
    report();
  });
  map.on(L.Draw.Event.EDITED, report);
  map.on(L.Draw.Event.DELETED, report);
}

/** The map of the journey: basemap, state lines, one marker per municipality with data, and the field drawing tool. */
export function FieldMap({ config, states, profiles, selected, municipality, explored, onSelect, onArea }: FieldMapProps) {
  const container = useRef<HTMLDivElement>(null);
  const map = useRef<L.Map | null>(null);
  const outline = useRef<L.GeoJSON | null>(null);
  const searched = useRef<L.GeoJSON | null>(null);
  const markers = useRef(new Map<string, L.CircleMarker>());

  useEffect(() => {
    const created = L.map(container.current!, { zoomControl: false, maxZoom: MAX_ZOOM }).fitBounds(BRAZIL);
    L.control.zoom({ position: "bottomleft" }).addTo(created);
    baseLayer(config).addTo(created);
    L.geoJSON(states as never, { style: { color: "#ffffff", weight: 1, opacity: 0.55, fill: false }, interactive: false }).addTo(created);
    for (const profile of profiles) {
      const marker = L.circleMarker(position(profile), { radius: 9, weight: 3, color: "#ffffff", fillColor: "#377a4e", fillOpacity: 1 });
      marker.bindTooltip(profile.label, { direction: "top", offset: [0, -8] }).on("click", () => onSelect(profile.id)).addTo(created);
      markers.current.set(profile.id, marker);
    }
    void addDrawing(created, onArea);
    map.current = created;
    return () => void created.remove();
    // The map is created once; later changes arrive through the effects below.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    for (const [id, marker] of markers.current) marker.setStyle({ fillColor: id === selected?.id ? "#b88735" : "#377a4e" });
    if (selected) map.current?.flyTo(position(selected), PLACE_ZOOM, { duration: 1.6 });
    else map.current?.flyToBounds(BRAZIL, { duration: 1.2 });
  }, [selected]);

  useEffect(() => {
    outline.current?.remove();
    outline.current = municipality && map.current
      ? L.geoJSON(municipality as never, { style: { color: "#b88735", weight: 2, fillOpacity: 0.08 }, interactive: false }).addTo(map.current)
      : null;
  }, [municipality]);

  useEffect(() => {
    searched.current?.remove();
    searched.current = null;
    if (!explored || !map.current) return;
    searched.current = L.geoJSON(explored as never, { style: { color: "#ffffff", weight: 2, dashArray: "6 5", fillColor: "#ffffff", fillOpacity: 0.12 }, interactive: false }).addTo(map.current);
    map.current.flyToBounds(searched.current.getBounds(), { duration: 1.4, maxZoom: 10, padding: [40, 40] });
  }, [explored]);

  return <div ref={container} className="field-map" aria-label="Map of municipalities with data" />;
}
