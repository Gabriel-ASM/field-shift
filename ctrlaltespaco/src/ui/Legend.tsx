import { cropColor, cropLabel } from "./colors.ts";

export function Legend({ crops }: { crops: string[] }) {
  return (
    <ul className="legend">
      {crops.map((crop) => (
        <li key={crop}><i style={{ background: cropColor(crop) }} />{cropLabel(crop)}</li>
      ))}
    </ul>
  );
}
