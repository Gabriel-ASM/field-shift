/** The plan: the result screen of the team's page (field_shift/front/producer.js, showFarmerResult), on the v2 run. */

import { useState } from "react";
import { MethodDialog } from "../method/MethodDialog.tsx";
import { rank, recommended, type RankedRoute } from "../ranking.ts";
import { Alternatives, Facts } from "../result/Facts.tsx";
import { ResultMetrics } from "../result/ResultMetrics.tsx";
import { RotationPath } from "../result/RotationPath.tsx";
import { YourChoices } from "../result/YourChoices.tsx";
import type { RunResult, ScenarioResult } from "../types.ts";
import type { Journey } from "../useFieldShift.ts";
import { cropLabel } from "../ui/colors.ts";
import { EnvironmentChart } from "../ui/EnvironmentChart.tsx";
import { count, money } from "../ui/format.ts";
import { Legend } from "../ui/Legend.tsx";
import { ReturnChart } from "../ui/ReturnChart.tsx";
import { Timebar } from "../ui/Timebar.tsx";
import { TrackStrips } from "../ui/TrackStrips.tsx";

const EXPLORATORY = 4;

function Actions({ journey }: { journey: Journey }) {
  return (
    <div className="actions">
      <button type="button" onClick={journey.restart}>Explore another scenario</button>
      <button type="button" className="primary" onClick={() => journey.go("priority")}>Adjust my priorities</button>
    </div>
  );
}

/** No sequence reached the recommendation threshold: show the best exploratory ones, plainly labelled. */
function Exploratory({ ranked, run, journey }: { ranked: RankedRoute[]; run: RunResult; journey: Journey }) {
  return (
    <section>
      <h2>No sequence has enough scenarios for a recommendation</h2>
      <p className="note">A recommendation needs at least {count(run.ranking.support.minimum_recommended)} valid NPVs for one sequence. These are exploratory; run more scenarios to firm them up.</p>
      <div className="alternatives">
        {ranked.slice(0, EXPLORATORY).map(({ route }) => (
          <div key={route.crops.join()} className="alternative-route"><strong>{route.crops.map(cropLabel).join(" → ")}</strong><span>{money(route.value!.p50)}/ha · {count(route.value!.count)} NPVs</span></div>
        ))}
      </div>
      <Actions journey={journey} />
    </section>
  );
}

function Heading({ single, explain }: { single: boolean; explain: () => void }) {
  return (
    <div className="result-heading">
      <p className="kicker">Your plan is ready</p>
      <h2>{single ? "A plan to grow more and care for the land" : "A crop rotation to grow more and care for the land"}</h2>
      <p className="lead">This is the sequence that best balances the priorities you chose.</p>
      <button className="method-trigger" type="button" aria-haspopup="dialog" onClick={explain}>
        <span className="method-question" aria-hidden="true">?</span><span>Wanna know how it was calculated?</span><span aria-hidden="true">→</span>
      </button>
    </div>
  );
}

function Unfolded({ run, scenario, cuts }: { run: RunResult; scenario: ScenarioResult; cuts: number | null }) {
  return (
    <article className="card unfolded">
      <h3>How the scenarios unfolded</h3>
      <Timebar periodsPerYear={run.clock.periods / run.clock.horizon_years} />
      <Legend crops={run.crops.filter((crop) => scenario.occupancy.some((period) => crop in period))} />
      <TrackStrips tracks={scenario.tracks} cuts={cuts} />
      <EnvironmentChart water={scenario.water} carbon={scenario.carbon} />
    </article>
  );
}

export function ResultStep({ journey }: { journey: Journey }) {
  const [explaining, setExplaining] = useState(false);
  const run = journey.run!;
  const scenario = run.scenarios[0]!;
  const ranked = rank(scenario.routes, scenario.ranking_reference, run.ranking, journey);
  const best = recommended(ranked, run.ranking);
  if (!ranked.length) {
    return <section><h2>We couldn't rank a rotation</h2><p className="note">No simulated sequence has complete price and cost data from at least {count(run.ranking.support.minimum_ranked)} scenarios.</p><Actions journey={journey} /></section>;
  }
  if (!best) return <Exploratory ranked={ranked} run={run} journey={journey} />;
  const single = best.route.crops.length < 2;
  const facts = { model: run.model, ranking: run.ranking, periods: run.clock.periods, trajectories: scenario.trajectories,
    rankedRoutes: scenario.ranking_reference?.routes ?? 0, weight: journey.weight, returnWeight: journey.returnWeight };
  return (
    <section className="result">
      <Heading single={single} explain={() => setExplaining(true)} />
      <div className="result-hero">
        <article className="recommendation-card">
          <span className="result-eyebrow">✦ Best combination found</span>
          <h2>{single ? "Your suggested management plan" : "Your suggested sequence"}</h2>
          <p>Planned by crop cycles over a five-year horizon.</p>
          <RotationPath route={best.route} caneCut={journey.caneCut} />
        </article>
        <ResultMetrics route={best.route} settings={run.ranking} />
      </div>
      <ReturnChart value={best.route.value!} fullSupport={run.ranking.support.full_score} />
      <div className="result-info">
        <Facts journey={journey} run={run} scenario={scenario} best={best} />
        <Alternatives ranked={ranked.filter((item) => item !== best)} minimum={run.ranking.support.minimum_recommended} />
      </div>
      <Unfolded run={run} scenario={scenario} cuts={journey.place!.choices.sugarcane_cuts} />
      <YourChoices journey={journey} trajectories={scenario.trajectories} />
      <p className="note">An exploratory study based on municipal data and model assumptions. These values do not guarantee income and do not replace an agronomist's assessment of your field.</p>
      <Actions journey={journey} />
      <MethodDialog open={explaining} onClose={() => setExplaining(false)} facts={facts} />
    </section>
  );
}
