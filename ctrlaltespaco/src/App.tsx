import { CropStep } from "./journey/CropStep.tsx";
import { LocationStep } from "./journey/LocationStep.tsx";
import { PriorityStep } from "./journey/PriorityStep.tsx";
import { ResultStep } from "./journey/ResultStep.tsx";
import { SimulationStep } from "./journey/SimulationStep.tsx";
import { Steps } from "./journey/Steps.tsx";
import { MapScene } from "./scene/MapScene.tsx";
import { useJourney, useWorld, type Journey, type World } from "./useFieldShift.ts";

function Screen({ journey, world }: { journey: Journey; world: World }) {
  switch (journey.step) {
    case "location": return <LocationStep journey={journey} world={world} />;
    case "crop": return <CropStep journey={journey} />;
    case "priority": return <PriorityStep journey={journey} world={world} />;
    case "simulation": return <SimulationStep journey={journey} world={world} />;
    case "result": return <ResultStep journey={journey} />;
  }
}

export function App() {
  const { world, error } = useWorld();
  const journey = useJourney(world);
  if (error) return <p className="error fatal">Could not reach the Field Shift API: {error}</p>;
  if (!world) return <p className="loading">Loading…</p>;
  const choosePlace = (id: string) => {
    journey.choosePlace(world.profiles.find((profile) => profile.id === id)!);
    if (journey.step !== "location") journey.go("location");
  };
  return (
    <div className="app">
      <MapScene config={world.config} states={world.states} municipality={journey.place?.municipality ?? null}
        profiles={world.profiles} selected={journey.place?.profile ?? null} run={journey.run} onSelect={choosePlace} />
      <header>
        <h1>Field Shift</h1>
        <p>A crop rotation plan from NASA climate data and your priorities</p>
      </header>
      <aside className="panel">
        <Steps current={journey.step} />
        <Screen journey={journey} world={world} />
        {journey.step !== "simulation" && journey.error && <p className="error">{journey.error}</p>}
      </aside>
      <footer>Basemap: {world.config.basemap.attribution} · Boundaries: IBGE</footer>
    </div>
  );
}
