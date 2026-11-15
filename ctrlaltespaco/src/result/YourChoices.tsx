/** What the farmer chose for this plan, with a way back to change it. */

import type { Journey } from "../useFieldShift.ts";
import { cropLabel } from "../ui/colors.ts";
import { count, percent } from "../ui/format.ts";

export function YourChoices({ journey, trajectories }: { journey: Journey; trajectories: number }) {
  const place = journey.place!;
  const crop = journey.crop!;
  return (
    <article className="result-panel choices-summary">
      <h3>What you chose</h3>
      <dl>
        <dt>Farm</dt><dd>{place.profile.municipality.name} ({place.profile.municipality.uf})</dd>
        <dt>Crop in the field</dt><dd>{cropLabel(crop)}{crop === "sugarcane" ? `, cut ${journey.caneCut} of ${place.choices.sugarcane_cuts} next` : ""}</dd>
        <dt>Priorities</dt><dd>{percent(1 - journey.weight)} financial return · {percent(journey.weight)} soil and water</dd>
        <dt>Money judged by</dt><dd>{percent(journey.returnWeight)} high return (P95) · {percent(1 - journey.returnWeight)} worst outcomes (CVaR₅)</dd>
        <dt>Scenarios</dt><dd>{count(trajectories)}, seed {journey.seed}</dd>
      </dl>
      <div className="actions">
        <button type="button" onClick={() => journey.go("crop")}>Change crop</button>
        <button type="button" onClick={() => journey.go("priority")}>Change priorities</button>
      </div>
    </article>
  );
}
