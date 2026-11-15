/** P7: a one-page plan to print — the chosen sequence, its ZARC planting windows year by year, the three
 *  indicators and the sources. Hidden on screen; print CSS shows only this. */

import { useEffect, useState } from "react";
import { createPortal } from "react-dom";
import { getPlantingWindows } from "../api.ts";
import { nitrogenClass, type RankedRoute } from "../ranking.ts";
import type { PlantingWindows, Profile, RankingSettings } from "../types.ts";
import { cropLabel } from "../ui/colors.ts";
import { count, money, percent } from "../ui/format.ts";
import { groupTracks, type StripTrack } from "../ui/tracks.ts";
import { decendioName, plantings, windowText } from "./plan.ts";
import { mostFrequentWater } from "./ResultMetrics.tsx";

const SOIL = { low: "needs care", medium: "fair", high: "good" } as const;
const NITROGEN = { low: "below", medium: "near", high: "above" } as const;
const WATER = { water_low: "low", water_medium: "medium", water_high: "high" } as const;

function usePlantingWindows(profile: string): PlantingWindows | null {
  const [windows, setWindows] = useState<{ profile: string; windows: PlantingWindows } | null>(null);
  useEffect(() => {
    let live = true;
    getPlantingWindows(profile).then((found) => live && setWindows({ profile, windows: found }), () => undefined);
    return () => { live = false; };
  }, [profile]);
  return windows?.profile === profile ? windows.windows : null;
}

interface PrintPlanProps {
  profile: Profile;
  start: string;
  ranked: RankedRoute;
  settings: RankingSettings;
  tracks: StripTrack[] | null;
  periodsPerYear: number;
  years: number;
  seed: number;
  trajectories: number;
}

function Calendar({ tracks, periodsPerYear, windows, years }: Pick<PrintPlanProps, "tracks" | "periodsPerYear" | "years"> & { windows: PlantingWindows | null }) {
  const groups = tracks?.length ? groupTracks(tracks) : [];
  if (!groups.length) return <p>The planting calendar is still loading.</p>;
  const [main] = groups;
  const sown = plantings(main!.track, periodsPerYear);
  const share = main!.count / tracks!.length;
  return (
    <>
      <table className="print-calendar">
        <thead><tr><th>Year</th><th>Plant</th><th>Around</th><th>ZARC window {windows?.seasons.at(-1) ?? ""} (risk)</th></tr></thead>
        <tbody>
          {Array.from({ length: years }, (_, index) => index + 1).map((year) => {
            const rows = sown.filter((planting) => planting.year === year);
            if (!rows.length) return <tr key={year}><td>{year}</td><td colSpan={3}>No new planting: the field holds the crop already in it.</td></tr>;
            return rows.map((planting, row) => {
              const window = windows?.crops[planting.crop];
              const risk = window?.risk[String(planting.decendio)];
              return (
                <tr key={`${year}-${row}`}>
                  <td>{row ? "" : year}</td>
                  <td>{cropLabel(planting.crop)}</td>
                  <td>{decendioName(planting.decendio)}{risk === undefined && window ? " · outside the window" : ""}</td>
                  <td>{window ? windowText(window.risk) : windows ? "no published window" : "…"}</td>
                </tr>
              );
            });
          })}
        </tbody>
      </table>
      <p className="print-small">Planting dates follow the most common timeline of the simulated scenarios ({percent(share)} of those sampled), to about two weeks. Risk is the lowest published by MAPA ZARC for the crop in that ten-day period; check the window for your cultivar group and ZARC soil class.</p>
    </>
  );
}

/** "202610" → "Oct 2026". */
function referenceMonth(value: string): string {
  const match = /^(\d{4})-?(\d{2})$/.exec(value);
  return match ? new Date(Number(match[1]), Number(match[2]) - 1, 1).toLocaleDateString("en-GB", { month: "short", year: "numeric" }) : value;
}

export function PrintPlan({ profile, start, ranked, settings, tracks, periodsPerYear, years, seed, trajectories }: PrintPlanProps) {
  const windows = usePlantingWindows(profile.id);
  const route = ranked.route;
  const value = route.value!;
  const [water, share] = mostFrequentWater(route);
  const climate = profile.climate_history?.period;
  return createPortal(
    <article className="print-plan" aria-hidden="true">
      <header>
        <h1>Crop rotation plan · {profile.label}</h1>
        <p>Field starting with {cropLabel(start).toLowerCase()} · {years}-year horizon · printed {new Date().toLocaleDateString("en-GB")} · Field Shift</p>
      </header>
      <section>
        <h2>Sequence</h2>
        <p className="print-sequence">{route.crops.map(cropLabel).join(" → ")}</p>
      </section>
      <section>
        <h2>When to plant, year by year</h2>
        <Calendar tracks={tracks} periodsPerYear={periodsPerYear} windows={windows} years={years} />
      </section>
      <section>
        <h2>What to expect</h2>
        <dl className="print-indicators">
          <div><dt>Net income</dt><dd>{money(value.p50)}/ha</dd><dd className="print-small">median present value over {years} years; 90% of scenarios between {money(value.p5)} and {money(value.p95)}</dd></div>
          <div><dt>Soil</dt><dd>carbon {SOIL[route.final_carbon_class]}, total N {NITROGEN[nitrogenClass(route, settings)]} target</dd><dd className="print-small">{route.final_carbon.toFixed(1)} g/kg organic carbon, {count(Math.round(route.final_total_nitrogen))} kg/ha total N at the end</dd></div>
          <div><dt>Water</dt><dd>{WATER[water]}</dd><dd className="print-small">most frequent final condition ({percent(share)} of scenarios); mean {percent(route.final_water_fraction)} of capacity</dd></div>
        </dl>
        <p className="print-small">{count(value.count)} simulated scenarios of this sequence with complete prices and costs · seed {seed} · {count(trajectories)} trajectories in the regional run.</p>
      </section>
      <section>
        <h2>Sources</h2>
        <ul className="print-sources print-small">
          <li>Climate: NASA POWER daily data{climate ? `, ${climate[0].slice(0, 4)}–${climate[1].slice(0, 4)}` : ""}.</li>
          <li>Soil: ISRIC SoilGrids 2.0, organic carbon, total nitrogen and bulk density, 0–30 cm{profile.scope === "window_mean" ? ", mean of a ~3 km window around the city" : ""}.</li>
          <li>Crops grown in the region and their sequences: IBGE Produção Agrícola Municipal (PAM).</li>
          <li>Planting windows: {windows ? `${windows.source.publisher} ${windows.source.system}, season ${windows.seasons.at(-1) ?? ""}` : "MAPA ZARC"}.</li>
          <li>Prices and production costs: CONAB{profile.economics?.reference_currency_month ? `, BRL of ${referenceMonth(profile.economics.reference_currency_month)}` : ""}; yields: IBGE PAM.</li>
          <li>Nitrogen: legume fixation and maize response from Embrapa studies (Alves et al. 2006; Perin et al. 2004; Okito et al. 2004; Coelho et al. 1987) and the team's survey.</li>
        </ul>
        <p className="print-small">An exploratory study from municipal data and model assumptions. It does not guarantee income and does not replace an agronomist's assessment of your field.</p>
      </section>
    </article>,
    document.body,
  );
}
