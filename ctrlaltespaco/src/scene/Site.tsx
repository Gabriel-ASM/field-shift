import { Html } from "@react-three/drei";
import { toWorld } from "../geo/mercator.ts";
import type { Profile, RunResult } from "../types.ts";
import { ScenarioColumn } from "./ScenarioColumn.tsx";

const COLUMN_HEIGHT = 0.14;
const COLUMN_RADIUS = 0.007;
const COLUMN_GAP = 0.02;
const PIN_RADIUS = 0.004;

interface SiteProps {
  profile: Profile;
  selected: boolean;
  run: RunResult | null;
  onSelect: (id: string) => void;
}

/** A profile on the map: a pin, and when it is selected and simulated, one column per scenario. */
export function Site({ profile, selected, run, onSelect }: SiteProps) {
  const [x, z] = toWorld([profile.initial_node.climate.long, profile.initial_node.climate.lat]);
  const scenarios = selected && run ? run.scenarios : [];
  return (
    <group position={[x, 0, z]}>
      <mesh position-y={0.004} onClick={() => onSelect(profile.id)}>
        <cylinderGeometry args={[PIN_RADIUS, PIN_RADIUS, 0.008, 32]} />
        <meshStandardMaterial color={selected ? "#f8fafc" : "#cbd5e1"} emissive={selected ? "#38bdf8" : "#000000"} emissiveIntensity={0.6} />
      </mesh>
      {scenarios.map((scenario, index) => (
        <group key={scenario.id} position-x={(index - (scenarios.length - 1) / 2) * COLUMN_GAP} position-y={0.008}>
          <ScenarioColumn scenario={scenario} crops={run!.crops} height={COLUMN_HEIGHT} radius={COLUMN_RADIUS} />
        </group>
      ))}
      <Html position={[0, 0.012, 0.03]} center zIndexRange={[5, 0]} className={selected ? "site-label selected" : "site-label"}>
        <button type="button" onClick={() => onSelect(profile.id)}>{profile.label}</button>
      </Html>
    </group>
  );
}
