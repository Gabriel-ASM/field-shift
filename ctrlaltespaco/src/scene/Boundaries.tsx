import { useMemo } from "react";
import { toWorld } from "../geo/mercator.ts";
import type { Boundary, Position } from "../types.ts";

function rings(boundary: Boundary): Position[][] {
  return boundary.features.flatMap(({ geometry }) =>
    geometry.type === "Polygon" ? geometry.coordinates : geometry.coordinates.flat(),
  );
}

/** Vertex pairs, one pair per edge of every ring, at height `lift`. */
function segmentPositions(boundary: Boundary, lift: number): Float32Array {
  const values: number[] = [];
  for (const ring of rings(boundary)) {
    for (let i = 0; i + 1 < ring.length; i++) {
      const [ax, az] = toWorld(ring[i]!);
      const [bx, bz] = toWorld(ring[i + 1]!);
      values.push(ax, lift, az, bx, lift, bz);
    }
  }
  return new Float32Array(values);
}

interface BoundariesProps {
  boundary: Boundary;
  color: string;
  opacity?: number;
  lift?: number;
}

export function Boundaries({ boundary, color, opacity = 1, lift = 0.002 }: BoundariesProps) {
  const positions = useMemo(() => segmentPositions(boundary, lift), [boundary, lift]);
  return (
    <lineSegments>
      <bufferGeometry>
        <bufferAttribute attach="attributes-position" args={[positions, 3]} />
      </bufferGeometry>
      <lineBasicMaterial color={color} transparent opacity={opacity} />
    </lineSegments>
  );
}
