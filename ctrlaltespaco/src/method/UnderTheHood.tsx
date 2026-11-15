/** Tab 02 of "Behind your estimate": the decision engine, as in field_shift/front/index.html (#method-panel-technical).
 *  Every number comes from the run: horizon, steps, trajectories, ranked routes, Dirichlet α, Δt, λ, α, support. */

import type { ModelSettings, RankingSettings } from "../types.ts";
import { count, percent } from "../ui/format.ts";

export interface EngineFacts {
  model: ModelSettings;
  ranking: RankingSettings;
  periods: number;
  trajectories: number;
  rankedRoutes: number;
  weight: number;
  returnWeight: number;
}

const fixed = (value: number, digits = 2) => value.toFixed(digits);

function Node({ title, note, code, kind = "" }: { title: string; note: string; code: string; kind?: string }) {
  return <div className={`engine-node ${kind}`}><strong>{title}</strong><small>{note}</small><code>{code}</code></div>;
}

function EngineMap({ facts }: { facts: EngineFacts }) {
  return (
    <div className="engine-map" aria-label="Data, simulation, and decision pipeline">
      <section className="engine-column">
        <span className="engine-column-title">Data & priors</span>
        <Node title="Climate history" note="NASA POWER · historical year blocks" code="rain, ETo → environment" />
        <Node title="Regional crop prior" note="IBGE PAM · top-5 area shares" code={`P₀ + Dirichlet(α = ${facts.model.dirichlet_alpha})`} />
        <Node title="Initial soil" note="SoilGrids · 0–30 cm" code="SOC₀, available water capacity" />
        <Node title="Agronomy & economics" note="MAPA ZARC · PAM / CONAB" code="windows, cycles, yield, price, cost" />
      </section>
      <div className="engine-link" aria-hidden="true" />
      <section className="engine-column">
        <span className="engine-column-title">Monte Carlo kernel · one trajectory</span>
        <Node kind="is-core" title="1 · Sample an exogenous future" note="Climate blocks + posterior transition rows" code="ω⁽ᵏ⁾ ~ historical + posterior draws" />
        <Node kind="is-core" title="2 · Propagate the state" note="Water every half month; carbon by crop" code="xₜ = [cₜ, wₜ, sₜ, τₜ]" />
        <Node kind="is-core" title="3 · Draw a constrained transition" note="Environment reweights the regional prior" code="P(c′) ∝ P₀(c′) · Fw · Fs, c′ ∈ Ωₜ" />
        <Node kind="is-core" title="4 · Resolve events & cash flow" note="Plant, wait, harvest, form perennial, discount" code="NPV⁽ᵏ⁾ = Σ CFₜ / (1+r)^(dayₜ/365)" />
      </section>
      <div className="engine-link delay" aria-hidden="true" />
      <section className="engine-column">
        <span className="engine-column-title">Decision layer · N trajectories</span>
        <Node kind="is-output" title="Aggregate realized routes" note="Group identical crop sequences" code="{route⁽ʲ⁾, NPV⁽ʲ⁾, w, s}" />
        <Node kind="is-output" title="Measure return & downside" note="Distribution, not a point forecast" code="median · P95 · CVaR₅ · P(NPV < 0)" />
        <Node kind="is-output" title="Rank by your priorities" note="Economics, final soil and water, and sample support" code="arg maxⱼ Jⱼ → recommendation" />
      </section>
      <div className="engine-feedback"><span aria-hidden="true">→</span><span>Feedback: crop demand changes water; water and carbon change transition probabilities and yield.</span></div>
    </div>
  );
}

function Horizon({ model }: { model: ModelSettings }) {
  const months = model.horizon_years * 12;
  const x = (month: number) => 55 + (650 * month) / months;
  return (
    <section className="horizon-card">
      <div className="tech-card-heading">
        <div><h3>{months}-month event horizon</h3><p>One illustrative trajectory: the environment advances in half-month steps; Markov decisions occur only at eligible planting events.</p></div>
        <span className="tech-tag">Δt ≈ {fixed(model.period_days, 1)} days</span>
      </div>
      <div className="horizon-view" tabIndex={0} aria-label={`Scrollable ${months}-month model timeline`}>
        <svg viewBox="0 0 760 145" role="img" aria-label={`Crop events, environmental updates, and planting decisions across ${months} months`}>
          <text className="method-svg-label" x="55" y="15" style={{ fontSize: 8, textAnchor: "start" }}>CROP / EVENT CLOCK</text>
          <rect x="55" y="29" width="155" height="27" rx="5" fill="#dce9d9" /><rect x="210" y="29" width="185" height="27" rx="5" fill="#b9d1ba" /><rect x="395" y="29" width="105" height="27" rx="5" fill="#ece8dc" /><rect x="500" y="29" width="205" height="27" rx="5" fill="#82aa8c" />
          <text className="method-svg-label" x="132" y="46" style={{ fontSize: 8 }}>initial crop</text><text className="method-svg-label" x="302" y="46" style={{ fontSize: 8 }}>next crop</text>
          <text className="method-svg-label" x="447" y="46" style={{ fontSize: 8 }}>fallow</text><text className="method-svg-label" x="602" y="46" style={{ fontSize: 8, fill: "#fff" }}>next eligible crop</text>
          <line x1="55" y1="75" x2="705" y2="75" stroke="#b8cbc0" strokeDasharray="2 5" />
          <circle cx="210" cy="75" r="5" fill="#b6a66f" /><circle cx="395" cy="75" r="5" fill="#b6a66f" /><circle cx="500" cy="75" r="5" fill="#2c7b51" />
          <text className="method-svg-label" x="210" y="91" style={{ fontSize: 7 }}>harvest</text><text className="method-svg-label" x="395" y="91" style={{ fontSize: 7 }}>harvest</text><text className="method-svg-label" x="500" y="91" style={{ fontSize: 7 }}>plant</text>
          <line x1="55" y1="108" x2="705" y2="108" stroke="#cad6ca" />
          {Array.from({ length: model.horizon_years + 1 }, (_, year) => (
            <g key={year}>
              <line x1={x(year * 12)} y1="103" x2={x(year * 12)} y2="113" stroke="#cad6ca" />
              <text className="method-svg-label" x={x(year * 12)} y="130" style={{ fontSize: 8 }}>{year === model.horizon_years ? `${months} mo` : year * 12}</text>
            </g>
          ))}
          <path className="horizon-cursor" d="M55 21V113" stroke="#2c7b51" strokeWidth="1.5" />
        </svg>
      </div>
      <div className="horizon-caption">
        <span><i /> Crop state / event</span><span><i /> {model.periods_per_year} environment updates per year</span>
        <span><i /> Harvest or decision</span><span>{model.decision_steps_per_year} decêndios per year · ZARC eligibility</span>
      </div>
    </section>
  );
}

function StateCard() {
  const items = [
    ["cₜ", "Crop / fallow", "Current state and consecutive plantings"], ["wₜ", "Water", "Storage fraction and low / medium / high class"],
    ["sₜ", "Soil carbon", "SOC in g/kg, updated by crop hypothesis"], ["τₜ", "Event clock", "Cycle, maturation, calendar, pending planting"],
  ];
  return (
    <section className="tech-card">
      <div className="tech-card-heading"><div><h3>State vector & feasible set</h3><p>Every simulated decision sees the current state and its constraints.</p></div><span className="tech-tag">xₜ → Ωₜ</span></div>
      <div className="state-vector">xₜ = [ cₜ, wₜ, sₜ, τₜ ]</div>
      <div className="state-list">{items.map(([code, title, note]) => <div key={code} className="state-item"><code>{code}</code><strong>{title}</strong><small>{note}</small></div>)}</div>
      <div className="constraint-title">Feasible destinations Ωₜ</div>
      <div className="constraint-list"><span>MAPA ZARC windows</span><span>one main crop</span><span>perennial maturation</span><span>fallow intervals</span></div>
    </section>
  );
}

function RiskCard({ facts }: { facts: EngineFacts }) {
  const { support } = facts.ranking;
  return (
    <section className="tech-card">
      <div className="tech-card-heading"><div><h3>Risk & multi-objective ranking</h3><p>Upside and downside are evaluated over each route’s NPV distribution.</p></div><span className="tech-tag">λ = {fixed(facts.weight)}</span></div>
      <div className="risk-visual">
        <svg viewBox="0 0 360 112" role="img" aria-label="NPV distribution showing worst five percent tail, median, and ninety-fifth percentile">
          <line x1="20" y1="88" x2="342" y2="88" stroke="#d5dfd4" />
          <path d="M25 88C45 86 53 72 70 62S93 27 127 23 174 33 197 49 238 72 270 78 319 84 338 88Z" fill="#e9f0e6" />
          <path d="M25 88C45 86 53 72 70 62L76 88Z" fill="#e7d6bd" />
          <path className="risk-curve" d="M25 88C45 86 53 72 70 62S93 27 127 23 174 33 197 49 238 72 270 78 319 84 338 88" fill="none" stroke="#548466" strokeWidth="2" />
          <line x1="72" y1="54" x2="72" y2="93" stroke="#b28c58" /><line x1="164" y1="28" x2="164" y2="93" stroke="#2c7b51" strokeDasharray="3 3" /><line x1="302" y1="73" x2="302" y2="93" stroke="#739ba8" />
          <text className="method-svg-label" x="72" y="105" style={{ fontSize: 7 }}>CVaR₅</text><text className="method-svg-label" x="164" y="105" style={{ fontSize: 7 }}>median</text><text className="method-svg-label" x="302" y="105" style={{ fontSize: 7 }}>P95</text>
        </svg>
      </div>
      <div className="risk-legend"><span><i /> worst 5% mean</span><span><i /> typical outcome</span><span><i /> high return</span></div>
      <div className="risk-formula">CVaR₅ = mean of the lowest ⌈0.05 × n⌉ NPVs</div>
      <div className="objective-formula">E = α·P95 + (1−α)·CVaR₅ → E₁₀<br />J = (1−w)[(1−λ)E₁₀ + λ(⅔S₁₀ + ⅓W₁₀)] + w·A₁₀</div>
      <p className="objective-meta">
        α = {fixed(facts.returnWeight)} · w = {fixed(support.weight)} · all component scores use a 0–10 scale. The curve here is illustrative.{" "}
        A recommendation requires at least {count(support.minimum_recommended)} valid NPVs per route. Sample support is worth {percent(support.weight)} of
        the score and reaches its maximum at {count(support.full_score)} valid NPVs.
      </p>
    </section>
  );
}

export function UnderTheHood({ facts }: { facts: EngineFacts }) {
  return (
    <>
      <div className="engine-status">
        <span className="engine-live"><i /> COUPLED DECISION ENGINE</span>
        <div className="engine-metrics">
          <span>T = {facts.model.horizon_years * 12} months</span><span>{count(facts.periods)} environment steps</span>
          <span>{count(facts.trajectories)} trajectories</span><span>{count(facts.rankedRoutes)} ranked routes</span>
        </div>
      </div>
      <EngineMap facts={facts} />
      <Horizon model={facts.model} />
      <div className="tech-grid"><StateCard /><RiskCard facts={facts} /></div>
      <p className="engine-footnote">Simulation-based search and ranking—not a claim of global agronomic optimality. Historical resampling explores variability; it is not a climate forecast. Hypotheses remain explicit and editable in Settings.</p>
    </>
  );
}
