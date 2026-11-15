import type { ScenarioResult } from "../types.ts";

const WIDTH = 180;
const HEIGHT = 70;
const WATER = [
  { id: "water_low", label: "low", color: "#d97757" },
  { id: "water_medium", label: "medium", color: "#e3c567" },
  { id: "water_high", label: "high", color: "#4f8fd0" },
] as const;

/** Share of trajectories in each soil-water class at the end of every year, as stacked bars. */
function WaterBars({ water }: { water: ScenarioResult["water"] }) {
  const step = WIDTH / water.length;
  return (
    <svg viewBox={`0 0 ${WIDTH} ${HEIGHT + 12}`} role="img" aria-label="Soil water classes per year">
      {water.map((year, index) => {
        let top = 0;
        return (
          <g key={index}>
            {WATER.map(({ id, color }) => {
              const height = (year[id] ?? 0) * HEIGHT;
              const bar = <rect key={id} x={index * step + 1} y={top} width={step - 2} height={height} fill={color} />;
              top += height;
              return bar;
            })}
            <text x={index * step + step / 2} y={HEIGHT + 10} textAnchor="middle">{index}</text>
          </g>
        );
      })}
    </svg>
  );
}

/** Soil carbon per year: the band holds 90% of trajectories, the line is the median. */
function CarbonBand({ carbon }: { carbon: ScenarioResult["carbon"] }) {
  const low = Math.min(...carbon.map((year) => year.p5));
  const high = Math.max(...carbon.map((year) => year.p95));
  const span = high - low || 1;
  const x = (index: number) => (index / (carbon.length - 1)) * WIDTH;
  const y = (value: number) => HEIGHT - ((value - low) / span) * (HEIGHT - 8) - 4;
  const upper = carbon.map((year, index) => `${x(index)},${y(year.p95)}`);
  const lower = carbon.map((year, index) => `${x(index)},${y(year.p5)}`).reverse();
  const median = carbon.map((year, index) => `${x(index)},${y(year.p50)}`).join(" ");
  return (
    <svg viewBox={`0 0 ${WIDTH} ${HEIGHT + 12}`} role="img" aria-label="Soil organic carbon per year">
      <polygon points={[...upper, ...lower].join(" ")} fill="#5fb3a1" opacity={0.3} />
      <polyline points={median} fill="none" stroke="#5fb3a1" strokeWidth={1.5} />
      <text x={0} y={HEIGHT + 10}>{carbon[0]!.p50.toFixed(1)} g/kg</text>
      <text x={WIDTH} y={HEIGHT + 10} textAnchor="end">{carbon.at(-1)!.p50.toFixed(1)} g/kg</text>
    </svg>
  );
}

interface EnvironmentChartProps {
  water: ScenarioResult["water"];
  carbon: ScenarioResult["carbon"];
}

export function EnvironmentChart({ water, carbon }: EnvironmentChartProps) {
  return (
    <>
      <h4>Soil at each year end</h4>
      <div className="environment">
        <figure>
          <WaterBars water={water} />
          <figcaption>Water in the soil: {WATER.map(({ label, color }) => <span key={label} style={{ color }}> {label}</span>)}</figcaption>
        </figure>
        <figure>
          <CarbonBand carbon={carbon} />
          <figcaption>Organic carbon, median and 90% range</figcaption>
        </figure>
      </div>
    </>
  );
}
