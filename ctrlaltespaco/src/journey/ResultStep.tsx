/** The plan: the result screen of the team's page (field_shift/front/producer.js, showFarmerResult), on the v2 run. */

import { useState } from "react";
import { MethodDialog } from "../method/MethodDialog.tsx";
import { options, rank, recommended, selectRoute, type RankedRoute } from "../ranking.ts";
import { Facts } from "../result/Facts.tsx";
import { RouteOptions } from "../result/RouteOptions.tsx";
import { useRouteDetail } from "../result/useRouteDetail.ts";
import { ResultMetrics } from "../result/ResultMetrics.tsx";
import { RotationPath } from "../result/RotationPath.tsx";
import { YourChoices } from "../result/YourChoices.tsx";
import type { RouteDetail, RunResult } from "../types.ts";
import type { Journey } from "../useFieldShift.ts";
import { cropLabel } from "../ui/colors.ts";
import { EnvironmentFrames, NITROGEN_SERIES, SOIL_SERIES, WATER_SERIES } from "../ui/EnvironmentFrames.tsx";
import { count, money } from "../ui/format.ts";
import { Legend } from "../ui/Legend.tsx";
import { ReturnChart } from "../ui/ReturnChart.tsx";
import { Timebar } from "../ui/Timebar.tsx";
import { TrackStrips } from "../ui/TrackStrips.tsx";

const EXPLORATORY = 4;
const OPTIONS = 6;

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

/** Water and soil of the sequence on screen, every ~15 days: the cards of the team's result page. */
function Frames({ detail, error, years, recommended }: { detail: RouteDetail | null; error: string | null; years: number; recommended: boolean }) {
  if (error) return <article className="result-chart-card"><p className="error">{error}</p></article>;
  if (!detail) return <article className="result-chart-card"><p className="note">Loading the scenarios of this sequence…</p></article>;
  const along = recommended ? "along the recommended sequence" : "along this sequence";
  return (
    <div className="environment-results-grid">
      <EnvironmentFrames frames={detail.frames.water} series={WATER_SERIES} years={years} text={{
        title: `Water ${along}`, description: "Share of matching scenarios in each water condition, measured every ~15 days.",
        label: `Continuous distribution of good, fair and bad water conditions over ${years * 12} months` }} />
      <EnvironmentFrames frames={detail.frames.soil} series={SOIL_SERIES} years={years} text={{
        title: `Soil ${along}`, description: "Share of matching scenarios in each soil-carbon class, measured every ~15 days.",
        label: `Continuous distribution of good, fair and bad soil conditions over ${years * 12} months` }} />
      <EnvironmentFrames frames={detail.frames.nitrogen} series={NITROGEN_SERIES} years={years} text={{
        title: `Total N ${along}`, description: "Share of matching scenarios relative to the carbon-derived stock target (C:N 12:1).",
        label: `Distribution of total nitrogen stock relative to the carbon-derived target over ${years * 12} months`,
        hint: "Total nitrogen is not mineral or directly available nitrogen." }} />
    </div>
  );
}

function Unfolded({ run, detail, cuts }: { run: RunResult; detail: RouteDetail | null; cuts: number | null }) {
  if (!detail) return null;
  const crops = run.crops.filter((crop) => detail.tracks.some((track) => track.crop.includes(crop)));
  return (
    <article className="card unfolded">
      <h3>How the scenarios of this sequence unfolded</h3>
      <Timebar periodsPerYear={run.clock.periods / run.clock.horizon_years} />
      <Legend crops={crops} />
      <TrackStrips tracks={detail.tracks} cuts={cuts} />
    </article>
  );
}

export function ResultStep({ journey }: { journey: Journey }) {
  const [explaining, setExplaining] = useState(false);
  const [chosen, choose] = useState<string | null>(null);
  const run = journey.run!;
  const scenario = run.scenarios[0]!;
  const ranked = rank(scenario.routes, scenario.ranking_reference, run.ranking, journey);
  const best = recommended(ranked, run.ranking);
  const selected = selectRoute(ranked, run.ranking, chosen);
  const { detail, error } = useRouteDetail(journey.job, selected?.route.crops ?? []);
  if (!ranked.length) {
    return <section><h2>We couldn't rank a rotation</h2><p className="note">No simulated sequence has complete price and cost data from at least {count(run.ranking.support.minimum_ranked)} scenarios.</p><Actions journey={journey} /></section>;
  }
  if (!best || !selected) return <Exploratory ranked={ranked} run={run} journey={journey} />;
  const single = selected.route.crops.length < 2;
  const facts = { model: run.model, ranking: run.ranking, periods: run.clock.periods, trajectories: scenario.trajectories,
    rankedRoutes: scenario.ranking_reference?.routes ?? 0, weight: journey.weight, returnWeight: journey.returnWeight };
  return (
    <section className="result">
      <Heading single={single} explain={() => setExplaining(true)} />
      <div className="result-hero">
        <article className="recommendation-card">
          {selected === best
            ? <span className="result-eyebrow">✦ Best combination found</span>
            : <span className="result-eyebrow is-option">Another good option · score {selected.total.toFixed(1)} of 10 <button type="button" onClick={() => choose(null)}>Back to the recommended sequence</button></span>}
          <h2>{single ? "Your suggested management plan" : selected === best ? "Your suggested sequence" : "This sequence"}</h2>
          <p>Planned by crop cycles over a five-year horizon.</p>
          <RotationPath route={selected.route} caneCut={journey.caneCut} />
        </article>
        <ResultMetrics ranked={selected} settings={run.ranking} />
      </div>
      <Frames detail={detail} error={error} years={run.clock.horizon_years} recommended={selected === best} />
      <ReturnChart value={selected.route.value!} fullSupport={run.ranking.support.full_score} />
      <div className="result-info">
        <Facts journey={journey} run={run} scenario={scenario} best={selected} />
        <RouteOptions options={options(ranked, run.ranking, OPTIONS)} best={best} selected={selected} choose={choose} />
      </div>
      <Unfolded run={run} detail={detail} cuts={journey.place!.choices.sugarcane_cuts} />
      <YourChoices journey={journey} trajectories={scenario.trajectories} />
      <p className="note">An exploratory study based on municipal data and model assumptions. These values do not guarantee income and do not replace an agronomist's assessment of your field.</p>
      <Actions journey={journey} />
      <MethodDialog open={explaining} onClose={() => setExplaining(false)} facts={facts} />
    </section>
  );
}
