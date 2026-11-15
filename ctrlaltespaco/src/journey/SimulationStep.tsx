import type { Progress } from "../runJob.ts";
import type { Journey, World } from "../useFieldShift.ts";
import { count, percent } from "../ui/format.ts";
import { GrowthScene } from "../ui/GrowthScene.tsx";

/** Trajectories the engine has finished, as it reports them batch by batch. */
function Counter({ progress }: { progress: Progress | null }) {
  if (!progress) return <p className="note">Starting the simulation…</p>;
  const fraction = progress.total ? progress.done / progress.total : 0;
  return (
    <div className="run-progress">
      <div className="run-progress-track" role="progressbar" aria-valuemin={0} aria-valuemax={progress.total} aria-valuenow={progress.done}>
        <div style={{ width: `${100 * fraction}%` }} />
      </div>
      <p><strong>{count(progress.done)}</strong> of {count(progress.total)} scenarios simulated <span>{percent(fraction)}</span></p>
    </div>
  );
}

/** Shown while the engine runs: the growing field, and the true count of simulated scenarios. */
export function SimulationStep({ journey, world }: { journey: Journey; world: World }) {
  return (
    <section>
      <div className="growth-card">
        <GrowthScene crop={journey.crop ?? "soybean"} />
        <div className="growth-copy">
          <h2>We're growing possibilities</h2>
          <p className="lead">Simulating {count(world.config.run.trajectories)} scenarios of your region's climate and conditions.</p>
          {!journey.error && <Counter progress={journey.progress} />}
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
