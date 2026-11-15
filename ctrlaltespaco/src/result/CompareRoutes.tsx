/** Two sequences side by side with the same three cards: the recommendation (fixed, left) and an alternative the farmer
 *  picks from the good options (right). Confirming applies the alternative to the whole result view. */

import { routeKey, type RankedRoute } from "../ranking.ts";
import type { RankingSettings } from "../types.ts";
import { cropLabel } from "../ui/colors.ts";
import { count, money, percent } from "../ui/format.ts";
import { ResultMetrics } from "./ResultMetrics.tsx";

interface CompareRoutesProps {
  best: RankedRoute;
  /** The good options other than the recommendation, best first. */
  alternatives: RankedRoute[];
  /** The alternative on the right: always one of `alternatives` when there is any. */
  compared: RankedRoute | undefined;
  settings: RankingSettings;
  /** True when the compared sequence is the one the whole result shows. */
  confirmed: boolean;
  pick: (key: string) => void;
  onConfirm: () => void;
  onAdjust: () => void;
}

const names = (item: RankedRoute) => item.route.crops.map(cropLabel).join(" → ");

/** The other measures of a sequence that the three cards do not show. */
function Others({ ranked, settings }: { ranked: RankedRoute; settings: RankingSettings }) {
  const { route } = ranked;
  const value = route.value!;
  return (
    <dl className="compare-others">
      <dt>Chance of a negative NPV</dt><dd>{percent(value.loss_probability)}</dd>
      <dt>Valid NPVs (support)</dt><dd>{count(value.count)} of {count(settings.support.full_score)} for full support</dd>
      <dt>Largest yield loss from replanting</dt>
      <dd>{route.yield_penalty ? percent(Math.max(0, ...route.yield_penalty)) : "not modelled (nitrogen decides)"}</dd>
      <dt>Low water at the end</dt><dd>{percent(route.final_water.water_low)}</dd>
    </dl>
  );
}

export function CompareRoutes({ best, alternatives, compared, settings, confirmed, pick, onConfirm, onAdjust }: CompareRoutesProps) {
  const comparedKey = compared ? routeKey(compared.route) : null;
  return (
    <section className="compare" aria-label="Compare two sequences">
      <div className="compare-heading">
        <h3>Compare two sequences</h3>
        <p>The recommendation stays on the left. Pick a good option to compare it on the right.</p>
      </div>
      <div className="compare-grid">
        <div className="compare-col">
          <span className="compare-tag">Recommended · fixed</span>
          <strong className="compare-name">{names(best)}</strong>
          <ResultMetrics ranked={best} settings={settings} />
          <Others ranked={best} settings={settings} />
        </div>
        <div className="compare-col">
          <span className="compare-tag">Alternative</span>
          {compared ? (
            <>
              <strong className="compare-name">{names(compared)}</strong>
              <ResultMetrics ranked={compared} settings={settings} />
              <Others ranked={compared} settings={settings} />
            </>
          ) : (
            <div className="compare-empty">
              <strong>No other good option yet</strong>
              <p className="note">Under these priorities, only the recommended sequence reaches the threshold. Change your priorities to see other options.</p>
              <button type="button" onClick={onAdjust}>Adjust my priorities</button>
            </div>
          )}
        </div>
      </div>
      {alternatives.length ? (
        <div className="compare-options">
          <h4>Good options</h4>
          <div className="alternatives">
            {alternatives.map((item) => (
              <button key={routeKey(item.route)} type="button" className="alternative-route" aria-pressed={routeKey(item.route) === comparedKey}
                onClick={() => pick(routeKey(item.route))}>
                <strong>{names(item)}</strong>
                <span>{money(item.route.value!.p50)}/ha · {item.total.toFixed(1)}</span>
              </button>
            ))}
          </div>
        </div>
      ) : null}
      <div className="compare-actions">
        <button type="button" className="primary" disabled={!compared || confirmed} onClick={onConfirm}>
          {confirmed ? "Showing this sequence" : "Confirm this sequence"}
        </button>
      </div>
    </section>
  );
}
