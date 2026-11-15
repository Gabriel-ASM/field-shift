import type { RankingSettings } from "../types.ts";
import type { Journey, World } from "../useFieldShift.ts";
import { count, percent } from "../ui/format.ts";

/** Title of the soil-and-water balance: the steps of updatePriority (field_shift/front/producer.js), in points. */
function emphasis(weight: number): string {
  const points = Math.round(weight * 100);
  if (points === 0) return "Fully focused on returns";
  if (points < 20) return "Stronger focus on returns";
  if (points === 20) return "Balanced, with a focus on returns";
  if (points < 40) return "Balanced, with a focus on soil and water";
  if (points < 50) return "Stronger focus on soil and water";
  return "Soil and water come first";
}

/** λ: soil and water against financial return, within the adjustable part of the score. */
function Balance({ journey, settings }: { journey: Journey; settings: RankingSettings }) {
  const limits = settings.environment_weight;
  return (
    <div className="setting">
      <div className="poles">
        <span><strong>Higher returns</strong><small>The financial return of the rotation.</small></span>
        <span><strong>More soil and water</strong><small>Carbon, total nitrogen, and water in the ranking.</small></span>
      </div>
      <input type="range" min={0} max={limits.maximum_weight} step={limits.weight_step} value={journey.weight}
        aria-label="Weight of soil and water" onChange={(event) => journey.setWeight(Number(event.target.value))} />
      <p className="balance">
        <strong>{emphasis(journey.weight)}</strong>
        <span>{percent(1 - journey.weight)} financial return · {percent(journey.weight)} carbon, total nitrogen, and water · excluding fixed sample support</span>
      </p>
    </div>
  );
}

/** α: within the financial return, the high return (P95) against the average of the worst futures (CVaR5). */
// function ReturnMix({ journey, settings }: { journey: Journey; settings: RankingSettings }) {
//   return (
//     <div className="setting">
//       <div className="poles">
//         <span><strong>Safer in bad years</strong><small>Average of the worst 5% of futures (CVaR₅).</small></span>
//         <span><strong>Bigger upside</strong><small>High return, the 95th percentile (P95).</small></span>
//       </div>
//       <input type="range" min={0} max={1} step={settings.return_weight.step} value={journey.returnWeight}
//         aria-label="Weight of the high return against the worst outcomes" onChange={(event) => journey.setReturnWeight(Number(event.target.value))} />
//       <p className="balance">
//         <strong>How we judge the money</strong>
//         <span>{percent(journey.returnWeight)} high return (P95) · {percent(1 - journey.returnWeight)} worst outcomes (CVaR₅)</span>
//       </p>
//     </div>
//   );
// }

/** The fixed part of the score: how many scenarios stand behind a sequence. */
function SupportNote({ settings }: { settings: RankingSettings }) {
  const { weight, minimum_recommended: minimum, full_score: full } = settings.support;
  return (
    <p className="note">
      {percent(weight)} of the score is fixed: the number of scenarios behind a sequence, full at {count(full)}.
      A sequence needs at least {count(minimum)} complete scenarios to be recommended.
    </p>
  );
}

export function PriorityStep({ journey, world }: { journey: Journey; world: World }) {
  const settings = journey.place!.choices.ranking;
  return (
    <section>
      <p className="kicker">What matters most to you?</p>
      <h2>Let's balance it your way</h2>
      <p className="lead">Drag the sliders to give more weight to financial returns or to soil and water conservation.</p>
      <Balance journey={journey} settings={settings} />
      {/* <ReturnMix journey={journey} settings={settings} /> */}
      <SupportNote settings={settings} />
      <label className="seed">Random seed
        <input type="number" min={0} value={journey.seed} onChange={(event) => journey.setSeed(Number(event.target.value) || 0)} />
      </label>
      <p className="note">{count(world.config.run.trajectories)} scenarios. The same seed reproduces a result exactly.</p>
      <div className="actions">
        <button type="button" onClick={() => journey.go("crop")}>Adjust crop</button>
        <button type="button" className="primary" onClick={journey.simulate}>Find my crop rotation</button>
      </div>
    </section>
  );
}
