import type { Journey } from "../useFieldShift.ts";
import { cropLabel } from "../ui/colors.ts";
import { CropArt } from "../ui/CropArt.tsx";

const ORDINAL = new Intl.PluralRules("en-US", { type: "ordinal" });
const SUFFIX: Record<string, string> = { one: "st", two: "nd", few: "rd", other: "th" };
const ordinal = (value: number) => `${value}${SUFFIX[ORDINAL.select(value)]}`;

/** The cuts offered: from the 2nd to the 5th (or the last modeled one). The 1st cut is not offered: the model does not
 *  behave well from it. */
export const FIRST_CUT = 2;
export const LAST_CUT = 5;

/** For standing cane: which of the modeled harvests comes next. The last one is followed by a reform. */
function CaneCut({ journey, cuts }: { journey: Journey; cuts: number }) {
  const last = Math.min(LAST_CUT, cuts);
  return (
    <fieldset className="cane-cut">
      <legend>Which cut comes next?</legend>
      <div role="group">
        {Array.from({ length: last - FIRST_CUT + 1 }, (_, index) => index + FIRST_CUT).map((cut) => (
          <button key={cut} type="button" aria-pressed={cut === journey.caneCut} onClick={() => journey.chooseCaneCut(cut)}>{ordinal(cut)}</button>
        ))}
      </div>
      <small>The model harvests a cane field {cuts} times, then reforms it. After the {ordinal(cuts)} cut the field is replanted.</small>
    </fieldset>
  );
}

export function CropStep({ journey }: { journey: Journey }) {
  const cuts = journey.place?.choices.sugarcane_cuts;
  const crops = journey.place?.choices.initial_crops ?? [];
  return (
    <section>
      <h2>What do you grow today?</h2>
      <p className="lead">The crop in the field now is where every scenario starts.</p>
      <div className="choices">
        {crops.map((crop) => (
          <button key={crop} type="button" className="choice" aria-pressed={crop === journey.crop} onClick={() => journey.chooseCrop(crop)}>
            <CropArt crop={crop} />
            <strong>{cropLabel(crop)}</strong>
          </button>
        ))}
      </div>
      {journey.crop === "sugarcane" && cuts && cuts >= FIRST_CUT ? <CaneCut journey={journey} cuts={cuts} /> : null}
      <div className="actions">
        <button type="button" onClick={() => journey.go("location")}>Back</button>
        <button type="button" className="primary" disabled={!journey.crop} onClick={() => journey.go("priority")}>Continue</button>
      </div>
    </section>
  );
}
