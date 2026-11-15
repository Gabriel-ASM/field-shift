/** Tab 01 of "Behind your estimate": five ideas, as in field_shift/front/index.html (#method-panel-simple). */

import { count } from "../ui/format.ts";

function MarkovCard() {
  return (
    <article className="method-card">
      <div className="method-visual">
        <svg viewBox="0 0 300 126" role="img" aria-label="Animated transitions between three crop states">
          <path className="markov-link" d="M70 66C91 29 109 29 130 66" /><path className="markov-link" d="M170 66C191 29 209 29 230 66" /><path className="markov-link" d="M230 91C190 116 110 116 70 91" />
          <circle className="markov-halo" cx="50" cy="73" r="28" /><circle className="markov-halo delay-one" cx="150" cy="73" r="28" /><circle className="markov-halo delay-two" cx="250" cy="73" r="28" />
          <circle className="markov-node" cx="50" cy="73" r="23" /><circle className="markov-node" cx="150" cy="73" r="23" /><circle className="markov-node" cx="250" cy="73" r="23" />
          <text className="method-svg-label" x="50" y="76">Crop A</text><text className="method-svg-label" x="150" y="76">Crop B</text><text className="method-svg-label" x="250" y="76">Crop C</text>
        </svg>
      </div>
      <div className="method-copy"><span className="method-step">01 · States and transitions</span><h3>Markov chain</h3><p>Each crop is a state. Regional history, water, and soil guide the odds of the next crop.</p></div>
    </article>
  );
}

function MonteCarloCard({ futures }: { futures: number }) {
  return (
    <article className="method-card">
      <div className="method-visual">
        <span className="method-count">{count(futures)} futures</span>
        <svg viewBox="0 0 300 126" role="img" aria-label="Animated lines representing many possible climate futures">
          <line x1="25" y1="105" x2="280" y2="105" stroke="#d9e3d8" />
          <path className="mc-line" d="M22 92C62 83 62 43 105 57S161 96 194 65 241 25 280 42" stroke="#2c7b51" />
          <path className="mc-line" d="M22 92C57 99 85 63 115 72S161 37 199 54 239 85 280 60" stroke="#7fa489" />
          <path className="mc-line" d="M22 92C62 63 85 94 120 63S172 72 201 88 247 52 280 72" stroke="#b1a56c" />
          <path className="mc-line" d="M22 92C53 78 89 33 124 52S171 84 208 43 248 68 280 28" stroke="#87a9b2" />
        </svg>
      </div>
      <div className="method-copy"><span className="method-step">02 · Many possible futures</span><h3>Monte Carlo</h3><p>We simulate many plausible climate and crop futures—not just one forecast.</p></div>
    </article>
  );
}

function NpvCard({ years }: { years: number }) {
  return (
    <article className="method-card">
      <div className="method-visual">
        <svg viewBox="0 0 300 126" role="img" aria-label="Animated cash-flow bars discounted to present value">
          <line x1="27" y1="102" x2="278" y2="102" stroke="#cbd8cc" /><line x1="27" y1="25" x2="27" y2="102" stroke="#cbd8cc" />
          <rect className="npv-bar" x="48" y="65" width="27" height="37" rx="4" fill="#9dbaa4" /><rect className="npv-bar" x="91" y="48" width="27" height="54" rx="4" fill="#80a78b" />
          <rect className="npv-bar" x="134" y="33" width="27" height="69" rx="4" fill="#5b9270" /><rect className="npv-bar" x="177" y="52" width="27" height="50" rx="4" fill="#80a78b" />
          <rect className="npv-bar" x="220" y="22" width="27" height="80" rx="4" fill="#2c7b51" />
          <text className="method-svg-label" x="150" y="119" style={{ fontSize: 9, fontWeight: 600 }}>Five years → today's value</text>
        </svg>
      </div>
      <div className="method-copy"><span className="method-step">03 · Value over time</span><h3>NPV</h3><p>Income and costs over {years === 5 ? "five" : years} years are discounted to today for a fair comparison in R$/ha.</p></div>
    </article>
  );
}

function WaterMethod() {
  return (
    <article className="environment-method">
      <svg viewBox="0 0 80 70" role="img" aria-label="Rain feeding an animated water reserve">
        <path d="M22 23h34a9 9 0 0 0 0-18 14 14 0 0 0-26-3A11 11 0 0 0 22 23Z" fill="#fff" stroke="#87a9b2" strokeWidth="1.6" />
        <path className="rain-drop" d="M29 27v6" stroke="#5b91ad" strokeWidth="2" strokeLinecap="round" /><path className="rain-drop drop-two" d="M40 27v6" stroke="#5b91ad" strokeWidth="2" strokeLinecap="round" /><path className="rain-drop drop-three" d="M51 27v6" stroke="#5b91ad" strokeWidth="2" strokeLinecap="round" />
        <path d="M17 45h47l-5 20H22Z" fill="#dcecf0" stroke="#87a9b2" strokeWidth="1.4" /><path className="water-wave" d="M21 52q5-4 10 0t10 0 10 0 9 0" fill="none" stroke="#5b91ad" strokeWidth="2" />
      </svg>
      <div><h3>Water</h3><p>NASA POWER rain and evaporation update water storage every half month, adjusted for crop demand.</p></div>
    </article>
  );
}

function SoilMethod() {
  return (
    <article className="environment-method">
      <svg viewBox="0 0 80 70" role="img" aria-label="Soil layers with animated organic carbon and a growing plant">
        <path d="M12 43h56v19H12Z" fill="#e6ddcb" /><path d="M12 51h56M12 57h56" stroke="#c2ae8d" />
        <path d="M40 45V25m0 10c-9 0-13-5-13-12 9 0 13 5 13 12Zm0-5c0-9 5-14 14-14 0 9-5 14-14 14Z" fill="#f5f8f3" stroke="#5b9270" strokeWidth="1.8" strokeLinejoin="round" />
        <circle className="carbon-dot" cx="23" cy="49" r="2" fill="#8b7657" /><circle className="carbon-dot dot-two" cx="48" cy="54" r="2" fill="#8b7657" /><circle className="carbon-dot dot-three" cx="59" cy="47" r="2" fill="#8b7657" />
      </svg>
      <div><h3>Soil</h3><p>SoilGrids sets the starting organic carbon and nitrogen. Each crop then changes it through explicit, exploratory assumptions.</p></div>
    </article>
  );
}

export function HowItWorks({ futures, years }: { futures: number; years: number }) {
  return (
    <>
      <div className="method-grid"><MarkovCard /><MonteCarloCard futures={futures} /><NpvCard years={years} /></div>
      <div className="environment-methods"><WaterMethod /><SoilMethod /></div>
      <div className="method-resilience">
        <span aria-hidden="true">✦</span>
        <div><strong>Why this matters for a changing climate</strong><p>Testing many futures helps reveal rotations that remain viable when conditions change. This supports more resilient decisions—it does not guarantee outcomes.</p></div>
      </div>
    </>
  );
}
