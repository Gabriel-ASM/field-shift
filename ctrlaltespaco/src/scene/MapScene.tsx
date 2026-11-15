import { Canvas } from "@react-three/fiber";
import { useMemo } from "react";
import { tilesAround, tilesCovering, toWorld } from "../geo/mercator.ts";
import type { Boundary, Position, Profile, RunResult, RuntimeConfig } from "../types.ts";
import { Basemap } from "./Basemap.tsx";
import { Boundaries } from "./Boundaries.tsx";
import { CameraRig, type View } from "./CameraRig.tsx";
import { Site } from "./Site.tsx";

const NORTH_WEST: Position = [-84, 14];
const SOUTH_EAST: Position = [-28, -42];
const COUNTRY_ZOOM = 5;
const DETAIL_RADIUS = 2;
const COUNTRY_VIEW: View = { target: toWorld([-53, -14]), height: 4.4, back: 2.4 };

function siteView(profile: Profile): View {
  const { long, lat } = profile.initial_node.climate;
  return { target: toWorld([long, lat]), height: 0.42, back: 0.5 };
}

interface MapSceneProps {
  config: RuntimeConfig;
  states: Boundary | null;
  municipality: Boundary | null;
  profiles: Profile[];
  selected: Profile | null;
  run: RunResult | null;
  onSelect: (id: string) => void;
}

export function MapScene({ config, states, municipality, profiles, selected, run, onSelect }: MapSceneProps) {
  const country = useMemo(() => tilesCovering(NORTH_WEST, SOUTH_EAST, COUNTRY_ZOOM), []);
  const detail = useMemo(() => {
    if (!selected) return [];
    const { long, lat } = selected.initial_node.climate;
    return tilesAround([long, lat], config.basemap.max_zoom, DETAIL_RADIUS);
  }, [selected, config.basemap.max_zoom]);
  return (
    <Canvas camera={{ position: [COUNTRY_VIEW.target[0], 7, COUNTRY_VIEW.target[1] + 4], fov: 38, near: 0.01, far: 60 }} dpr={[1, 2]}>
      <color attach="background" args={["#05080d"]} />
      <ambientLight intensity={1.1} />
      <directionalLight position={[4, 8, 2]} intensity={1.6} />
      <Basemap tiles={country} template={config.basemap.tiles} />
      <Basemap tiles={detail} template={config.basemap.tiles} lift={0.0008} />
      {states && <Boundaries boundary={states} color="#e2e8f0" opacity={0.35} />}
      {municipality && <Boundaries boundary={municipality} color="#38bdf8" lift={0.003} />}
      {profiles.map((profile) => (
        <Site key={profile.id} profile={profile} selected={profile.id === selected?.id} run={run} onSelect={onSelect} />
      ))}
      <CameraRig view={selected ? siteView(selected) : COUNTRY_VIEW} />
    </Canvas>
  );
}
