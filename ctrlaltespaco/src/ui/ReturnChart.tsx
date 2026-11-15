/** "Return distribution for the recommended sequence": the smoothed present values of one route, with the worst-5%
 *  tail shaded and lines at CVaR5, median and P95. Layout of renderReturnChart in field_shift/front/producer.js. */

import { useId } from "react";
import type { ValueSummary } from "../types.ts";
import { density, type Density } from "./density.ts";
import { count, money } from "./format.ts";

const WIDTH = 760, HEIGHT = 225, LEFT = 46, RIGHT = 33, TOP = 25, BOTTOM = 174;
const TICKS = 4;

const COMPACT = new Intl.NumberFormat("en-US", { style: "currency", currency: "BRL", notation: "compact", maximumFractionDigits: 1 });

interface Marker {
  key: "cvar5" | "p50" | "p95";
  label: string;
  note: string;
  color: string;
  dash: string;
  className: string;
}

const MARKERS: Marker[] = [
  { key: "cvar5", label: "CVaR₅", note: "Average of the worst outcomes", color: "#8b5725", dash: "2 3", className: "return-tail" },
  { key: "p50", label: "Median", note: "Middle outcome", color: "#25674a", dash: "6 4", className: "return-median" },
  { key: "p95", label: "P95", note: "95th percentile", color: "#326e85", dash: "10 3 2 3", className: "return-p95" },
];

function scaleX(curve: Density) {
  return (value: number) => LEFT + ((WIDTH - LEFT - RIGHT) * (value - curve.minimum)) / (curve.maximum - curve.minimum);
}

function paths(curve: Density): { line: string; area: string } {
  const x = scaleX(curve);
  const peak = Math.max(...curve.points.map((point) => point.density), 1);
  const line = curve.points
    .map(({ value, density: height }, index) => `${index ? "L" : "M"}${x(value).toFixed(2)} ${(BOTTOM - ((BOTTOM - TOP) * height) / peak).toFixed(2)}`)
    .join(" ");
  return { line, area: `${line} L ${WIDTH - RIGHT} ${BOTTOM} L ${LEFT} ${BOTTOM} Z` };
}

function Axis({ curve }: { curve: Density }) {
  const x = scaleX(curve);
  const ticks = Array.from({ length: TICKS + 1 }, (_, index) => curve.minimum + ((curve.maximum - curve.minimum) * index) / TICKS);
  return (
    <>
      <line x1={LEFT} y1={BOTTOM} x2={WIDTH - RIGHT} y2={BOTTOM} stroke="#9caf9e" />
      {ticks.map((value) => (
        <g key={value}>
          <line x1={x(value)} y1={BOTTOM} x2={x(value)} y2={BOTTOM + 5} stroke="#9caf9e" />
          <text x={x(value)} y={BOTTOM + 21} textAnchor="middle" fill="#455c50" fontSize={12}>{COMPACT.format(value)}</text>
        </g>
      ))}
      <text x={WIDTH / 2} y={HEIGHT - 6} textAnchor="middle" fill="#455c50" fontSize={12}>Net present value (R$/ha)</text>
    </>
  );
}

function Chart({ value, curve }: { value: ValueSummary; curve: Density }) {
  const clip = `tail-${useId().replace(/:/g, "")}`;
  const x = scaleX(curve);
  const { line, area } = paths(curve);
  const label = `Smoothed net present value distribution, based on ${value.count} valid scenarios. ` +
    MARKERS.map(({ key, label: name }) => `${name}: ${money(value[key])} per hectare`).join("; ");
  return (
    <svg className="result-chart" id="return-distribution-chart" viewBox={`0 0 ${WIDTH} ${HEIGHT}`} role="img" aria-label={label}>
      <defs><clipPath id={clip}><rect x={LEFT} y={TOP - 2} width={Math.max(0, x(value.p5) - LEFT)} height={BOTTOM - TOP + 2} /></clipPath></defs>
      <path d={area} fill="#e6efe3" />
      <path d={area} fill="#ead4b2" clipPath={`url(#${clip})`} />
      <Axis curve={curve} />
      {MARKERS.map(({ key, label: name, color, dash }) => (
        <line key={key} x1={x(value[key])} y1={TOP} x2={x(value[key])} y2={BOTTOM} stroke={color} strokeWidth={1.7} strokeDasharray={dash}>
          <title>{`${name}: ${money(value[key])}/ha`}</title>
        </line>
      ))}
      <path d={line} fill="none" stroke="#377354" strokeWidth={2.5} strokeLinejoin="round" strokeLinecap="round" />
    </svg>
  );
}

/** Plain-language risk: P5 as "1 in 20 futures", CVaR5 as the average of those futures. */
function riskSentence(value: ValueSummary): string {
  const tail = Math.max(1, Math.ceil(value.count * 0.05));
  return `1 in 20 futures ends the five years below ${money(value.p5)}/ha; in those futures the average is ${money(value.cvar5)}/ha ` +
    `(CVaR₅, the mean of the ${count(tail)} lowest valid outcomes). The shaded area is that lower 5% tail.`;
}

export function ReturnChart({ value, fullSupport }: { value: ValueSummary; fullSupport: number }) {
  if (!value.distribution) return null;
  const curve = density(value.distribution);
  return (
    <article className="result-chart-card">
      <div className="result-chart-heading">
        <h3>Return distribution for the recommended sequence</h3>
        <span className="chart-badge">{count(value.count)} valid NPVs</span>
        <p>Five-year net present value per hectare, based on all valid calculations for this sequence. The curve smooths the simulated outcomes.</p>
      </div>
      <Chart value={value} curve={curve} />
      <div className="return-metrics">
        {MARKERS.map(({ key, label, note, className }) => (
          <span key={key} className={className}><strong>{label}</strong><b>{money(value[key])}/ha</b><small>{note}</small></span>
        ))}
      </div>
      <p className="result-chart-summary">{riskSentence(value)}{value.count < fullSupport ? " Small sample; the tail estimates can vary substantially." : ""}</p>
    </article>
  );
}
