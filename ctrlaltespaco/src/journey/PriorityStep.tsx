import type { Journey, World } from "../useFieldShift.ts";
import { count, percent } from "../ui/format.ts";

function emphasis(weight: number, maximum: number): string {
  if (weight === 0) return "Financial return only";
  if (weight >= maximum) return "Balanced between returns and conservation";
  return weight <= maximum / 2 ? "Balanced, with a focus on returns" : "Balanced, with more care for soil and water";
}

export function PriorityStep({ journey, world }: { journey: Journey; world: World }) {
  const limits = journey.place!.choices.ranking.environment_weight;
  return (
    <section>
      <h2>Let's balance it your way</h2>
      <p className="lead">Drag the slider to give more weight to financial returns or to soil and water conservation.</p>
      <div className="poles">
        <span><strong>Higher returns</strong><small>The financial return of the rotation.</small></span>
        <span><strong>More soil and water</strong><small>The conservation of natural resources.</small></span>
      </div>
      <input type="range" min={0} max={limits.maximum_weight} step={limits.weight_step} value={journey.weight}
        aria-label="Weight of soil and water" onChange={(event) => journey.setWeight(Number(event.target.value))} />
      <p className="balance">
        <strong>{emphasis(journey.weight, limits.maximum_weight)}</strong>
        <span>{percent(1 - journey.weight)} financial return · {percent(journey.weight)} soil and water</span>
      </p>
      <label className="seed">Random seed
        <input type="number" min={0} value={journey.seed} onChange={(event) => journey.setSeed(Number(event.target.value) || 0)} />
      </label>
      <p className="note">{count(world.config.run.trajectories)} scenarios. The same seed reproduces a result exactly.</p>
      <div className="actions">
        <button type="button" onClick={() => journey.go("crop")}>Adjust crop</button>
        <button type="button" className="primary" onClick={journey.simulate}>Find my crop rotation</button>
      </div>
    </section>
  );
}
