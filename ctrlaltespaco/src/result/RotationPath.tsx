/** "Your suggested sequence": one card per planting with the crop's drawing, as showFarmerResult in producer.js. */

import type { Route } from "../types.ts";
import { cropLabel } from "../ui/colors.ts";
import { CropArt } from "../ui/CropArt.tsx";
import { percent } from "../ui/format.ts";

function position(index: number, crop: string, caneCut: number): string {
  if (index > 0) return `Planting ${index + 1}`;
  return crop === "sugarcane" ? `Current crop · cut ${caneCut} next` : "Current crop";
}

export function RotationPath({ route, caneCut }: { route: Route; caneCut: number }) {
  return (
    <div className="rotation-path">
      {route.crops.map((crop, index) => {
        const penalty = route.yield_penalty?.[index] ?? 0;
        return (
          <div key={index} className={index === 0 ? "rotation-crop is-current" : "rotation-crop"} style={{ animationDelay: `${index * 0.22}s` }}>
            <CropArt crop={crop} size={48} />
            <strong>{cropLabel(crop)}</strong>
            <small>{position(index, crop, caneCut)}</small>
            {penalty > 0 && <small>−{percent(penalty)} yield at harvest</small>}
          </div>
        );
      })}
    </div>
  );
}
