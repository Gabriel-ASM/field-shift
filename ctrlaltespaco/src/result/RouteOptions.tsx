/** "Good options": the sequences that could be recommended. Choosing one shows it in the whole result view. */

import { routeKey, type RankedRoute } from "../ranking.ts";
import { cropLabel } from "../ui/colors.ts";
import { money } from "../ui/format.ts";

export function RouteOptions({ options, best, selected, choose }: {
  options: RankedRoute[]; best: RankedRoute; selected: RankedRoute; choose: (key: string | null) => void;
}) {
  return (
    <article className="result-panel">
      <h3>Good options</h3>
      <p>Choose a sequence to see it above. Scores follow your priorities.</p>
      <div className="alternatives">
        {options.map((item) => (
          <button key={routeKey(item.route)} type="button" className="alternative-route" aria-pressed={item === selected}
            onClick={() => choose(item === best ? null : routeKey(item.route))}>
            <strong>{item.route.crops.map(cropLabel).join(" → ")}{item === best ? " · recommended" : ""}</strong>
            <span>{money(item.route.value!.p50)}/ha · {item.total.toFixed(1)}</span>
          </button>
        ))}
      </div>
    </article>
  );
}
