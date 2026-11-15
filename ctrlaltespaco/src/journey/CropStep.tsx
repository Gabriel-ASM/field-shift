import type { Journey } from "../useFieldShift.ts";
import { cropColor, cropLabel } from "../ui/colors.ts";

export function CropStep({ journey }: { journey: Journey }) {
  const crops = journey.place?.choices.initial_crops ?? [];
  return (
    <section>
      <h2>What do you grow today?</h2>
      <p className="lead">The crop in the field now is where every scenario starts.</p>
      <div className="choices">
        {crops.map((crop) => (
          <button key={crop} type="button" className="choice" aria-pressed={crop === journey.crop} onClick={() => journey.chooseCrop(crop)}>
            <i style={{ background: cropColor(crop) }} />
            <strong>{cropLabel(crop)}</strong>
          </button>
        ))}
      </div>
      <div className="actions">
        <button type="button" onClick={() => journey.go("location")}>Back</button>
        <button type="button" className="primary" disabled={!journey.crop} onClick={() => journey.go("priority")}>Continue</button>
      </div>
    </section>
  );
}
