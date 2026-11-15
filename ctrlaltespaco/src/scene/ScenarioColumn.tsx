import { useFrame } from "@react-three/fiber";
import { useRef } from "react";
import type { Mesh } from "three";
import { playhead } from "../state/playhead.ts";
import type { ScenarioResult } from "../types.ts";
import { cropColor } from "../ui/colors.ts";
import { sharesAt } from "./occupancy.ts";

interface ScenarioColumnProps {
  scenario: ScenarioResult;
  crops: string[];
  height: number;
  radius: number;
}

/** A column split by crop: each slice is as tall as the share of trajectories in that crop right now. */
export function ScenarioColumn({ scenario, crops, height, radius }: ScenarioColumnProps) {
  const slices = useRef<(Mesh | null)[]>([]);
  useFrame(() => {
    const shares = sharesAt(scenario.occupancy, crops, playhead.period);
    let base = 0;
    shares.forEach((share, index) => {
      const slice = slices.current[index];
      if (!slice) return;
      const tall = share * height;
      slice.visible = tall > 1e-4;
      slice.scale.y = Math.max(tall, 1e-4);
      slice.position.y = base + tall / 2;
      base += tall;
    });
  });
  return (
    <group>
      {crops.map((crop, index) => (
        <mesh key={crop} ref={(mesh) => void (slices.current[index] = mesh)}>
          <cylinderGeometry args={[radius, radius, 1, 32]} />
          <meshStandardMaterial color={cropColor(crop)} roughness={0.55} />
        </mesh>
      ))}
    </group>
  );
}
