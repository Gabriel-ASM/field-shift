import type { ScenarioResult, ValueSummary } from "../types.ts";
import { cropColor, cropLabel } from "./colors.ts";
import { money, percent } from "./format.ts";
import { TrackStrips } from "./TrackStrips.tsx";

function Route({ crops }: { crops: string[] }) {
  return (
    <span className="route">
      {crops.map((crop, index) => (
        <i key={index} style={{ background: cropColor(crop) }} title={cropLabel(crop)} />
      ))}
    </span>
  );
}

function Value({ value, scale }: { value: ValueSummary; scale: [number, number] }) {
  const place = (amount: number) => `${((amount - scale[0]) / (scale[1] - scale[0])) * 100}%`;
  return (
    <div className="value">
      <strong>{money(value.p50)}</strong>
      <span>median present value per hectare, 5 years</span>
      <div className="range" aria-label={`5% to 95%: ${money(value.p5)} to ${money(value.p95)}`}>
        <b style={{ left: place(value.p5), right: `calc(100% - ${place(value.p95)})` }} />
        <i style={{ left: place(value.p50) }} />
        <u style={{ left: place(0) }} />
      </div>
      <small>
        {money(value.p5)} to {money(value.p95)} in 90% of trajectories
      </small>
    </div>
  );
}

interface ScenarioCardProps {
  scenario: ScenarioResult;
  scale: [number, number];
}

export function ScenarioCard({ scenario, scale }: ScenarioCardProps) {
  const unpriced = 1 - scenario.priced_share;
  return (
    <article className="scenario">
      <h3>{scenario.label}</h3>
      {scenario.value ? <Value value={scenario.value} scale={scale} /> : <p className="note">No trajectory could be priced.</p>}
      {unpriced > 0.005 && (
        <p className="note">{percent(unpriced)} of trajectories pass through a crop without cost or price data and are left out of the value.</p>
      )}
      <TrackStrips tracks={scenario.tracks} />
      <ol className="routes">
        {scenario.routes.slice(0, 3).map((route, index) => (
          <li key={index}>
            <Route crops={route.crops} />
            <span>{percent(route.share)}</span>
          </li>
        ))}
      </ol>
    </article>
  );
}
