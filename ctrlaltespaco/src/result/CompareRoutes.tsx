/** Two sequences side by side with the same three cards: the recommendation (fixed, left) and an alternative the farmer
 *  is comparing (right). Confirming applies the alternative to the whole result view. */

import { routeKey, type RankedRoute } from "../ranking.ts";
import type { RankingSettings } from "../types.ts";
import { cropLabel } from "../ui/colors.ts";
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
        </div>
        <div className="compare-col">
          <span className="compare-tag">Alternative</span>
          {shown ? (
            <>
              <strong className="compare-name">{names(shown)}</strong>
              <ResultMetrics ranked={shown} settings={settings} />
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
