/** Cards shown while the analysis runs (docs/microlearning-espera.md, English copy). They only fill the wait: nothing
 *  here delays or changes the result. */

export interface Card {
  title: string;
  body: string;
}

export const CARDS: readonly Card[] = [
  { title: "Many futures", body: "We don't forecast one year. Each simulated scenario draws its own sequence of weather years from the region's history." },
  { title: "Crop states", body: "Each crop is a state. Regional history, water and soil guide the odds of the next crop in the sequence." },
  { title: "Water in the soil", body: "Rain and evaporation update the water in the soil every half month, adjusted for what each crop needs." },
  { title: "Value over time", body: "Income and costs over five years are brought to today's value in R$/ha. A harvest later counts for less than one now." },
  { title: "Median net income", body: "The estimated net income is the median: half of the scenarios end above it and half below." },
  { title: "CVaR₅: the bad years", body: "CVaR₅ is the average of the worst 5% of outcomes. It shows how bad a bad year can get." },
  { title: "P95: the good years", body: "P95 is the value that only 5% of scenarios beat. It measures the upside of a sequence." },
  { title: "Soil carbon", body: "Soil carbon changes slowly, season by season. A sequence that keeps carbon up protects the land for the next cycle." },
  { title: "Total nitrogen is not fertilizer", body: "Total nitrogen is the stock in the soil, not the nitrogen a crop can use right now." },
  { title: "Support", body: "A sequence with few valid NPVs is a weak guide. Support grows with the number of scenarios behind it." },
  { title: "Compare before you confirm", body: "A higher median can come with a worse bad-year outcome. The comparison shows what you give up." },
  { title: "Estimates, not guarantees", body: "These are estimates from municipal data and model assumptions. An agronomist should check them against your field." },
];

/** A random permutation of `items` (Fisher–Yates); the input is left as it is. */
export function shuffled<T>(items: readonly T[], random: () => number = Math.random): T[] {
  const out = [...items];
  for (let i = out.length - 1; i > 0; i--) {
    const j = Math.floor(random() * (i + 1));
    [out[i], out[j]] = [out[j]!, out[i]!];
  }
  return out;
}
