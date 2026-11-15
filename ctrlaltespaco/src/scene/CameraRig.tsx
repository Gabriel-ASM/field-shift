import { MapControls } from "@react-three/drei";
import { useThree } from "@react-three/fiber";
import gsap from "gsap";
import { useEffect, useRef, type ComponentRef } from "react";

export interface View {
  /** World point the camera looks at. */
  target: [x: number, z: number];
  /** Camera height above the ground and distance south of the target. */
  height: number;
  back: number;
}

const FLIGHT_SECONDS = 2.2;

/** Map-style controls; whenever `view` changes the camera flies there. */
export function CameraRig({ view }: { view: View }) {
  const controls = useRef<ComponentRef<typeof MapControls>>(null);
  const camera = useThree((state) => state.camera);
  const [x, z] = view.target;
  useEffect(() => {
    const target = controls.current?.target;
    if (!target) return;
    const flight = gsap.timeline({ defaults: { duration: FLIGHT_SECONDS, ease: "power3.inOut" }, onUpdate: () => controls.current?.update() });
    flight.to(target, { x, y: 0, z }, 0).to(camera.position, { x, y: view.height, z: z + view.back }, 0);
    return () => void flight.kill();
  }, [camera, x, z, view.height, view.back]);
  return <MapControls ref={controls} makeDefault maxPolarAngle={Math.PI / 2.3} minDistance={0.15} maxDistance={9} />;
}
