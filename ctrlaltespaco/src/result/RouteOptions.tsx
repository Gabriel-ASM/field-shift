/** "Good options": the sequences that could be recommended. Choosing one sets the alternative in the comparison;
 *  the whole result view changes only when the farmer confirms it. */

import { routeKey, type RankedRoute } from "../ranking.ts";
import { cropLabel } from "../ui/colors.ts";
import { money } from "../ui/format.ts";

export function RouteOptions({ options, best, compared, pick }: {
  options: RankedRoute[]; best: RankedRoute; compared: RankedRoute | undefined; pick: (key: string) => void;
}) {
  const comparedKey = compared ? routeKey(compared.route) : null;
  return (
    <article className="result-panel">
      <h3>Good options</h3>
      <p>Choose a sequence to compare it with the recommendation. Scores follow your priorities.</p>
      <div className="alternatives">
        {options.map((item) => (
          <button key={routeKey(item.route)} type="button" className="alternative-route" aria-pressed={routeKey(item.route) === comparedKey}
            onClick={() => pick(routeKey(item.route))}>
            <strong>{item.route.crops.map(cropLabel).join(" → ")}{item === best ? " · recommended" : ""}</strong>
            <span>{money(item.route.value!.p50)}/ha · {item.total.toFixed(1)}</span>
          </button>
        ))}
      </div>
    </article>
  );
}
