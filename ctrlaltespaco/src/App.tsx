import { MapScene } from "./scene/MapScene.tsx";
import type { Profile, RunResult } from "./types.ts";
import { cropLabel } from "./ui/colors.ts";
import { count } from "./ui/format.ts";
import { Legend } from "./ui/Legend.tsx";
import { RotationEditor } from "./ui/RotationEditor.tsx";
import { ScenarioCard } from "./ui/ScenarioCard.tsx";
import { Timebar } from "./ui/Timebar.tsx";
import { useSimulation, useWorld, type Simulation } from "./useFieldShift.ts";

/** One money scale for every scenario card, so their ranges can be compared by eye. */
function valueScale(run: RunResult): [number, number] {
  const values = run.scenarios.flatMap(({ value }) => (value ? [value.p5, value.p95] : []));
  return [Math.min(0, ...values), Math.max(0, ...values)];
}

function cropsShown(run: RunResult): string[] {
  const seen = new Set(run.scenarios.flatMap(({ occupancy }) => occupancy.flatMap((year) => Object.keys(year))));
  return run.crops.filter((crop) => seen.has(crop));
}

function Results({ run }: { run: RunResult }) {
  const scale = valueScale(run);
  return (
    <>
      <Timebar periodsPerYear={run.clock.periods / run.clock.horizon_years} />
      <Legend crops={cropsShown(run)} />
      {run.scenarios.map((scenario) => <ScenarioCard key={scenario.id} scenario={scenario} scale={scale} />)}
      <p className="note">
        {count(run.scenarios[0]?.trajectories ?? 0)} trajectories per scenario, simulated on the {run.device.toUpperCase()} in {run.seconds} s.
        Both scenarios face the same sampled climate. Exploratory, not agronomic advice.
      </p>
    </>
  );
}

/** Every municipality as a button, so a place is always reachable even when the map pin is out of view. */
function Places({ profiles, selected, onSelect }: { profiles: Profile[]; selected: string | null; onSelect: (profile: Profile) => void }) {
  return (
    <nav className="places" aria-label="Municipalities">
      {profiles.map((profile) => (
        <button key={profile.id} type="button" aria-pressed={profile.id === selected} onClick={() => onSelect(profile)}>
          {profile.label}
        </button>
      ))}
    </nav>
  );
}

function Panel({ simulation, profiles }: { simulation: Simulation; profiles: Profile[] }) {
  const { selection, sequence, start, seed, run, running, error } = simulation;
  const places = <Places profiles={profiles} selected={selection?.profile.id ?? null} onSelect={simulation.select} />;
  if (!selection) {
    return (
      <aside className="panel">
        <p className="hint">Choose a municipality here or on the map.</p>
        {places}
        {error && <p className="error">{error}</p>}
      </aside>
    );
  }
  return (
    <aside className="panel">
      {places}
      <h2>{selection.profile.label}</h2>
      <form className="controls" onSubmit={(event) => { event.preventDefault(); simulation.simulate(); }}>
        <label htmlFor="start-crop">Crop in the field today</label>
        <select id="start-crop" value={start} onChange={(event) => simulation.setStart(event.target.value)}>
          {selection.startCrops.map((crop) => <option key={crop} value={crop}>{cropLabel(crop)}</option>)}
        </select>
        <label>Rotation to compare</label>
        <RotationEditor crops={selection.crops} sequence={sequence} onChange={simulation.setSequence} />
        <div className="row">
          <label>Seed <input type="number" min={0} value={seed} onChange={(event) => simulation.setSeed(Number(event.target.value) || 0)} /></label>
          <button type="submit" disabled={running}>{running ? "Simulating…" : "Simulate"}</button>
        </div>
      </form>
      {error && <p className="error">{error}</p>}
      {run && <Results run={run} />}
    </aside>
  );
}

export function App() {
  const { world, error } = useWorld();
  const simulation = useSimulation(world);
  if (error) return <p className="error fatal">Could not reach the Field Shift API: {error}</p>;
  if (!world) return <p className="loading">Loading…</p>;
  const selected = simulation.selection;
  return (
    <div className="app">
      <MapScene config={world.config} states={world.states} municipality={selected?.municipality ?? null}
        profiles={world.profiles} selected={selected?.profile ?? null} run={simulation.run}
        onSelect={(id) => simulation.select(world.profiles.find((profile) => profile.id === id)!)} />
      <header>
        <h1>Field Shift</h1>
        <p>Crop rotations under sampled climate, per municipality</p>
      </header>
      <Panel simulation={simulation} profiles={world.profiles} />
      <footer>Basemap: {world.config.basemap.attribution} · Boundaries: IBGE</footer>
    </div>
  );
}
