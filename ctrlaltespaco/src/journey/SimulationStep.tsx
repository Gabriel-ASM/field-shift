import gsap from "gsap";
import { useEffect, useRef } from "react";
import type { Journey, World } from "../useFieldShift.ts";
import { count } from "../ui/format.ts";

/** Shown while the engine runs. The bar only signals activity: the engine answers in one piece. */
export function SimulationStep({ journey, world }: { journey: Journey; world: World }) {
  const bar = useRef<HTMLDivElement>(null);
  useEffect(() => {
    const pulse = gsap.fromTo(bar.current, { xPercent: -100 }, { xPercent: 250, duration: 1.4, ease: "power1.inOut", repeat: -1 });
    return () => void pulse.kill();
  }, []);
  return (
    <section>
      <h2>We're growing possibilities</h2>
      <p className="lead">Simulating {count(world.config.run.trajectories)} scenarios of your region's climate and conditions.</p>
      <div className="progress"><div ref={bar} /></div>
      {journey.error ? (
        <>
          <p className="error">We couldn't complete the analysis: {journey.error}</p>
          <div className="actions"><button type="button" onClick={() => journey.go("priority")}>Back</button>
            <button type="button" className="primary" onClick={journey.simulate}>Try again</button></div>
        </>
      ) : <p className="note">There's nothing else you need to do. Your plan appears here as soon as it is ready.</p>}
    </section>
  );
}
