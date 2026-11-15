import type { Journey, World } from "../useFieldShift.ts";
import { count } from "../ui/format.ts";
import { GrowthScene } from "../ui/GrowthScene.tsx";

/** Shown while the engine runs. The engine answers in one piece, so the scene loops without any progress count. */
export function SimulationStep({ journey, world }: { journey: Journey; world: World }) {
  return (
    <section>
      <div className="growth-card">
        <GrowthScene crop={journey.crop ?? "soybean"} />
        <div className="growth-copy">
          <h2>We're growing possibilities</h2>
          <p className="lead">Simulating {count(world.config.run.trajectories)} scenarios of your region's climate and conditions, all at once.</p>
          {journey.error ? (
            <>
              <p className="error">We couldn't complete the analysis: {journey.error}</p>
              <div className="actions"><button type="button" onClick={() => journey.go("priority")}>Back</button>
                <button type="button" className="primary" onClick={journey.simulate}>Try again</button></div>
            </>
          ) : <p className="note">There's nothing else you need to do. Your plan appears here as soon as it is ready.</p>}
        </div>
      </div>
    </section>
  );
}
