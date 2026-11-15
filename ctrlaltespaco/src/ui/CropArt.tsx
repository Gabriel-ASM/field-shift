import { cropShapes } from "./cropArt.ts";

/** The crop's drawing as the paths of an SVG, to place inside another SVG. */
export function CropShapes({ crop }: { crop: string }) {
  return <>{cropShapes(crop).map(({ d, fill }, index) => <path key={index} d={d} fill={fill} />)}</>;
}

/** The crop's pixel-art drawing, `size` pixels wide. */
export function CropArt({ crop, size = 44 }: { crop: string; size?: number }) {
  return (
    <svg className="crop-art" width={size} height={size} viewBox="0 0 120 120" shapeRendering="crispEdges" aria-hidden="true">
      <CropShapes crop={crop} />
    </svg>
  );
}
