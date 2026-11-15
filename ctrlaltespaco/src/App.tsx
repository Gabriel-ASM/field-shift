import gsap from "gsap";
import { useEffect, useRef, useState } from "react";
import { CropStep } from "./journey/CropStep.tsx";
import { LocationStep } from "./journey/LocationStep.tsx";
import { PriorityStep } from "./journey/PriorityStep.tsx";
import { ResultStep } from "./journey/ResultStep.tsx";
import { SimulationStep } from "./journey/SimulationStep.tsx";
import { Steps } from "./journey/Steps.tsx";
import { FieldMap } from "./map/FieldMap.tsx";
import { useJourney, useWorld, type Journey, type World } from "./useFieldShift.ts";

const PANEL_WIDTH = "min(460px, 100vw)";

function Screen({ journey, world, area }: { journey: Journey; world: World; area: number | null }) {
  switch (journey.step) {
    case "location": return <LocationStep journey={journey} world={world} area={area} />;
    case "crop": return <CropStep journey={journey} />;
    case "priority": return <PriorityStep journey={journey} world={world} />;
    case "simulation": return <SimulationStep journey={journey} world={world} />;
    case "result": return <ResultStep journey={journey} />;
  }
}

/** The side panel grows from the right edge over the map when the plan is ready, and shrinks back afterwards. */
function usePanelWidth(wide: boolean) {
  const panel = useRef<HTMLElement>(null);
  useEffect(() => {
    if (!panel.current) return; // still loading: the panel is not on the page yet
    const tween = gsap.to(panel.current, { width: wide ? "100vw" : PANEL_WIDTH, duration: 0.9, ease: "power3.inOut" });
    return () => void tween.kill();
  }, [wide]);
  return panel;
}

export function App() {
  const { world, error } = useWorld();
  const journey = useJourney(world);
  const [area, setArea] = useState<number | null>(null);
  const wide = journey.step === "result";
  const panel = usePanelWidth(wide);
  // Each step starts at its top: the panel scrolls, and would otherwise keep the previous step's position.
  useEffect(() => {
    panel.current?.scrollTo({ top: 0 });
  }, [journey.step, panel]);
  if (error) return <p className="error fatal">Could not reach the Field Shift API: {error}</p>;
  if (!world) return <p className="loading">Loading…</p>;
  const choosePlace = (id: string) => {
    journey.choosePlace(world.profiles.find((profile) => profile.id === id)!);
    if (journey.step !== "location") journey.go("location");
  };
  return (
    <div className="app">
      <FieldMap config={world.config} states={world.states} profiles={world.profiles} selected={journey.place?.profile ?? null}
        municipality={journey.place?.municipality ?? null} onSelect={choosePlace} onArea={setArea} />
      <aside ref={panel} className={wide ? "panel wide" : "panel"}>
        <header>
          <strong>Field Shift</strong>
          <Steps current={journey.step} />
        </header>
        <Screen journey={journey} world={world} area={area} />
        {journey.step !== "simulation" && journey.error && <p className="error">{journey.error}</p>}
      </aside>
    </div>
  );
}
