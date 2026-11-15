/** Share of one route's trajectories in each water or soil class, every half month, as stacked areas, in a card.
 *  Card, layout, colours and interaction of renderEnvironmentOutcomeChart and the result cards of
 *  field_shift/front/producer.js and index.html (#farmer-water-chart, #farmer-soil-chart). */

import { useState, type KeyboardEvent, type PointerEvent } from "react";
import { count, percent } from "./format.ts";

const WIDTH = 640, HEIGHT = 260, LEFT = 42, RIGHT = 12, TOP = 20, BOTTOM = 216;
const PLOT_WIDTH = WIDTH - LEFT - RIGHT, PLOT_HEIGHT = BOTTOM - TOP;

export interface Series {
  index: number;        // column of the class in the counts: 0 low, 1 medium, 2 high
  label: string;
  color: string;
}

export const WATER_SERIES: Series[] = [
  { index: 2, label: "Good", color: "#4b91ad" }, { index: 1, label: "Fair", color: "#d6ad51" }, { index: 0, label: "Bad", color: "#cf7b6b" },
];
export const SOIL_SERIES: Series[] = [
  { index: 2, label: "Good", color: "#5c8d5a" }, { index: 1, label: "Fair", color: "#c59a50" }, { index: 0, label: "Bad", color: "#b97657" },
];
export const NITROGEN_SERIES: Series[] = [
  { index: 2, label: "Above target", color: "#5c8d5a" }, { index: 1, label: "Near target", color: "#c59a50" }, { index: 0, label: "Below target", color: "#b97657" },
];

const x = (period: number, last: number) => LEFT + (PLOT_WIDTH * period) / last;
const y = (fraction: number) => BOTTOM - PLOT_HEIGHT * fraction;

/** Upper edge of each series, stacked in order, as fractions of the trajectories in each period. */
function stack(frames: number[][], series: Series[]): number[][] {
  const totals = frames.map((row) => Math.max(1, row.reduce((sum, value) => sum + value, 0)));
  let lower = frames.map(() => 0);
  return series.map(({ index }) => (lower = lower.map((value, period) => value + frames[period]![index]! / totals[period]!)));
}

function Areas({ edges, series, last }: { edges: number[][]; series: Series[]; last: number }) {
  return (
    <>
      {edges.map((upper, layer) => {
        const lower = layer ? edges[layer - 1]! : upper.map(() => 0);
        const top = upper.map((value, period) => `${period ? "L" : "M"}${x(period, last).toFixed(2)} ${y(value).toFixed(2)}`).join(" ");
        const bottom = lower.map((value, period) => `L${x(period, last).toFixed(2)} ${y(value).toFixed(2)}`).reverse().join(" ");
        return <path key={series[layer]!.label} d={`${top} ${bottom} Z`} fill={series[layer]!.color} fillOpacity={0.9} stroke="#fff" strokeWidth={0.45} />;
      })}
    </>
  );
}

function Grid({ last, years }: { last: number; years: number }) {
  return (
    <>
      {[0, 0.25, 0.5, 0.75, 1].map((value) => (
        <g key={value}>
          <line x1={LEFT} y1={y(value)} x2={WIDTH - RIGHT} y2={y(value)} stroke="#fff" strokeOpacity={0.8} />
          <text x={LEFT - 7} y={y(value) + 3} textAnchor="end" fill="#68756c" fontSize={9}>{Math.round(value * 100)}%</text>
        </g>
      ))}
      {Array.from({ length: years + 1 }, (_, year) => {
        const at = x(Math.round((last * year) / years), last);
        return (
          <g key={year}>
            <line x1={at} y1={TOP} x2={at} y2={BOTTOM} stroke="#fff" strokeOpacity={0.65} />
            <text x={at} y={BOTTOM + 19} textAnchor="middle" fill="#68756c" fontSize={9}>{year === years ? `${years * 12} mo` : year * 12}</text>
          </g>
        );
      })}
      <text x={WIDTH - RIGHT} y={11} textAnchor="end" fill="#68756c" fontSize={9}>% of scenarios</text>
    </>
  );
}

interface CardText {
  title: string;
  description: string;
  label: string;        // aria label of the chart
  hint?: string;
}

const HINT = "Hover, touch, or focus and use the arrow keys to inspect a period.";

function nextPeriod(key: string, period: number, last: number): number | null {
  if (key === "ArrowLeft") return Math.max(0, period - 1);
  if (key === "ArrowRight") return Math.min(last, period + 1);
  if (key === "Home") return 0;
  if (key === "End") return last;
  return null;
}

export function EnvironmentFrames({ text, frames, series, years }: { text: CardText; frames: number[][]; series: Series[]; years: number }) {
  const last = frames.length - 1;
  const [period, setPeriod] = useState(last);
  if (last < 1) return null;
  const point = (event: PointerEvent<SVGRectElement>) => {
    const box = event.currentTarget.ownerSVGElement!.getBoundingClientRect();
    const at = ((event.clientX - box.left) * WIDTH) / Math.max(1, box.width);
    setPeriod(Math.min(last, Math.max(0, Math.round(((at - LEFT) / PLOT_WIDTH) * last))));
  };
  const key = (event: KeyboardEvent<SVGSVGElement>) => {
    const next = nextPeriod(event.key, Math.min(period, last), last);
    if (next === null) return;
    event.preventDefault();
    setPeriod(next);
  };
  const row = frames[Math.min(period, last)]!, total = Math.max(1, row.reduce((sum, value) => sum + value, 0));
  return (
    <article className="result-chart-card">
      <div className="result-chart-heading">
        <h3>{text.title}</h3><span className="chart-badge">{count(total)} scenarios</span><p>{text.description}</p>
      </div>
      <div className="result-chart-legend" aria-label={`${text.title} legend`}>
        {series.map(({ label, color }) => <span key={label}><i style={{ background: color }} />{label}</span>)}
      </div>
      <svg className="result-chart" viewBox={`0 0 ${WIDTH} ${HEIGHT}`} role="img" tabIndex={0} aria-label={text.label} onKeyDown={key}>
        <Areas edges={stack(frames, series)} series={series} last={last} />
        <Grid last={last} years={years} />
        <line x1={x(Math.min(period, last), last)} y1={TOP} x2={x(Math.min(period, last), last)} y2={BOTTOM} stroke="#263e31" strokeWidth={1.2} strokeDasharray="3 3" pointerEvents="none" />
        <rect x={LEFT} y={TOP} width={PLOT_WIDTH} height={PLOT_HEIGHT} fill="transparent" style={{ cursor: "crosshair" }} onPointerMove={point} onPointerDown={point} />
      </svg>
      <p className="chart-period-detail">
        Month {((Math.min(period, last) * years * 12) / last).toFixed(1)} · {count(total)} scenarios · {series.map(({ index, label }) => `${label} ${percent(row[index]! / total)}`).join(" · ")}
      </p>
      <p className="chart-interaction-hint">{text.hint ?? HINT}</p>
    </article>
  );
}
