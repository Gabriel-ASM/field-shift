/** Two sequences side by side with the same three cards: the recommendation (fixed, left) and an alternative the farmer
 *  is comparing (right). Confirming applies the alternative to the whole result view. */

import { routeKey, type RankedRoute } from "../ranking.ts";
import type { RankingSettings } from "../types.ts";
import { cropLabel } from "../ui/colors.ts";
import { count, percent } from "../ui/format.ts";
import { ResultMetrics } from "./ResultMetrics.tsx";

interface CompareRoutesProps {
  best: RankedRoute;
  /** The alternative on the right; undefined when there is none to compare. */
  compared: RankedRoute | undefined;
  settings: RankingSettings;
  /** True when the compared sequence is the one the whole result shows. */
  confirmed: boolean;
  onConfirm: () => void;
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

export function CompareRoutes({ best, compared, settings, confirmed, onConfirm }: CompareRoutesProps) {
  const shown = compared && routeKey(compared.route) !== routeKey(best.route) ? compared : undefined;
  return (
    <section className="compare" aria-label="Compare two sequences">
      <div className="compare-heading">
        <h3>Compare two sequences</h3>
        <p>The recommendation stays on the left. Pick another option below to compare it on the right.</p>
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
          {shown ? (
            <>
              <strong className="compare-name">{names(shown)}</strong>
              <ResultMetrics ranked={shown} settings={settings} />
              <Others ranked={shown} settings={settings} />
            </>
          ) : (
            <p className="note">Choose another good option to compare it here.</p>
          )}
        </div>
      </div>
      <div className="compare-actions">
        <button type="button" className="primary" disabled={!shown || confirmed} onClick={onConfirm}>
          {confirmed ? "Showing this sequence" : "Confirm this sequence"}
        </button>
      </div>
    </section>
  );
}
