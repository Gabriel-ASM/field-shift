import { exploratory, rank, recommended, weights, type RankedRoute } from "../ranking.ts";
import type { RunResult, ScenarioResult } from "../types.ts";
import type { Journey } from "../useFieldShift.ts";
import { cropColor, cropLabel } from "../ui/colors.ts";
import { CropArt } from "../ui/CropArt.tsx";
import { EnvironmentChart } from "../ui/EnvironmentChart.tsx";
import { count, money, percent } from "../ui/format.ts";
import { Legend } from "../ui/Legend.tsx";
import { Timebar } from "../ui/Timebar.tsx";
import { TrackStrips } from "../ui/TrackStrips.tsx";

const OTHERS = 4;

/** "In the field", with the next cut when the field is standing cane. */
function fieldLabel(crop: string, caneCut: number): string {
  return crop === "sugarcane" ? `In the field · cut ${caneCut} next` : "In the field";
}

function Sequence({ crops, caneCut }: { crops: string[]; caneCut: number }) {
  return (
    <ol className="sequence">
      {crops.map((crop, index) => (
        <li key={index} style={{ borderColor: cropColor(crop) }}>
          <CropArt crop={crop} size={36} />
          <span><small>{index === 0 ? fieldLabel(crop, caneCut) : `Planting ${index}`}</small>{cropLabel(crop)}</span>
        </li>
      ))}
    </ol>
  );
}

function Metric({ label, value, note }: { label: string; value: string; note: string }) {
  return <article className="metric"><span>{label}</span><strong>{value}</strong><small>{note}</small></article>;
}

function Metrics({ best }: { best: RankedRoute }) {
  const value = best.route.value!;
  return (
    <div className="metrics">
      <Metric label="Scenarios behind it" value={percent(best.route.share)} note={`${count(value.count)} priced scenarios followed this sequence. Evidence score ${best.support.toFixed(1)} / 10.`} />
      <Metric label="Estimated net income" value={money(value.p50)} note="Median present value over five years, per hectare." />
      <Metric label="Final soil condition" value={`${best.soil.toFixed(1)} / 10`} note={`${best.route.final_carbon.toFixed(1)} g/kg of organic carbon at the end.`} />
      <Metric label="Available water" value={`${best.water.toFixed(1)} / 10`} note="From the soil water classes at the end of the horizon." />
    </div>
  );
}

function Considered({ run, scenario, best, weight }: { run: RunResult; scenario: ScenarioResult; best: RankedRoute; weight: number }) {
  const value = best.route.value!;
  return (
    <ul className="considered">
      <li>{count(scenario.trajectories)} scenarios, each with climate years resampled from the NASA POWER record of the municipality.</li>
      <li>Your priorities: {percent(1 - weight)} financial return, {percent(weight)} soil and water. {percent(weights(weight, run.ranking).support)} of the score is the number of scenarios behind the sequence, up to {count(run.ranking.support.full_score)}. Score {best.total.toFixed(1)} of 10.</li>
      <li>{percent(best.route.share)} of the scenarios followed this sequence; in 90% of them the income stayed between {money(value.p5)} and {money(value.p95)}.</li>
      <li>Planting dates follow the MAPA ZARC windows; prices and costs come from IBGE and CONAB.</li>
      <li>Simulated on the {run.device.toUpperCase()} in {run.seconds} s, seed {run.seed}.</li>
    </ul>
  );
}

function Others({ ranked, run }: { ranked: RankedRoute[]; run: RunResult }) {
  if (!ranked.length) return <p className="note">No other sequence had enough scenarios to compare.</p>;
  return (
    <ol className="others">
      {ranked.map((item, index) => (
        <li key={index}>
          <span className="route">
            {item.route.crops.map((crop, position) => <i key={position} style={{ background: cropColor(crop) }} title={cropLabel(crop)} />)}
            {exploratory(item, run.ranking) && <small className="tag">exploratory · {count(item.route.value!.count)} scenarios</small>}
          </span>
          <span>{money(item.route.value!.p50)}</span>
          <span>{item.total.toFixed(1)}</span>
        </li>
      ))}
    </ol>
  );
}

export function ResultStep({ journey }: { journey: Journey }) {
  const run = journey.run!;
  const scenario = run.scenarios[0]!;
  const ranked = rank(scenario.routes, run.ranking, journey.weight);
  const best = recommended(ranked, run.ranking);
  const rest = ranked.filter((item) => item !== best);
  const actions = (
    <div className="actions">
      <button type="button" onClick={journey.restart}>Explore another scenario</button>
      <button type="button" className="primary" onClick={() => journey.go("priority")}>Adjust my priorities</button>
    </div>
  );
  if (!ranked.length) return <section><h2>We couldn't rank a rotation</h2><p className="note">No simulated sequence has complete price and cost data from at least {count(run.ranking.support.minimum_ranked)} scenarios.</p>{actions}</section>;
  if (!best) {
    return (
      <section>
        <h2>No sequence has enough scenarios for a recommendation</h2>
        <p className="note">A recommendation needs at least {count(run.ranking.support.minimum_recommended)} priced scenarios. These sequences are exploratory; run more scenarios to firm them up.</p>
        <Others ranked={rest.slice(0, OTHERS)} run={run} />
        {actions}
      </section>
    );
  }
  return (
    <section className="result">
      <div className="result-heading">
        <p className="kicker">Your plan is ready</p>
        <h2>A crop rotation to grow more and care for the land</h2>
        <p className="lead">The sequence that best balances the priorities you chose.</p>
      </div>
      <article className="recommendation">
        <h3>Your suggested sequence</h3>
        <Sequence crops={best.route.crops} caneCut={journey.caneCut} />
        <p className="note">Planned by crop cycles over a five-year horizon.</p>
      </article>
      <Metrics best={best} />
      <article className="card">
        <h3>What we considered</h3>
        <Considered run={run} scenario={scenario} best={best} weight={journey.weight} />
      </article>
      <article className="card">
        <h3>Other good options</h3>
        <Others ranked={rest.slice(0, OTHERS)} run={run} />
      </article>
      <article className="card unfolded">
        <h3>How the scenarios unfolded</h3>
        <Timebar periodsPerYear={run.clock.periods / run.clock.horizon_years} />
        <Legend crops={run.crops.filter((crop) => scenario.occupancy.some((period) => crop in period))} />
        <TrackStrips tracks={scenario.tracks} />
        <EnvironmentChart water={scenario.water} carbon={scenario.carbon} />
      </article>
      <p className="note">An exploratory study based on municipal data and model assumptions. These values do not guarantee income and do not replace an agronomist's assessment of your field.</p>
      {actions}
    </section>
  );
}
