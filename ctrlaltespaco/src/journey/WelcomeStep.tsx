import { useState } from "react";
import { MethodDialog } from "../method/MethodDialog.tsx";
import { CropShapes } from "../ui/CropArt.tsx";

const FIELD_CROPS = ["soybean", "maize_grain", "wheat", "sugarcane", "dry_bean", "brachiaria"];
const FIELD_PLANTS = Array.from({ length: 30 }, (_, index) => ({
  crop: FIELD_CROPS[(index + Math.floor(index / 6)) % FIELD_CROPS.length]!,
  x: (index % 6) * 132,
  y: Math.floor(index / 6) * 128,
}));

/** A quiet field of the same crop illustrations used throughout the planning journey. */
function PixelCropField() {
  return (
    <div className="welcome-field" aria-hidden="true">
      <svg viewBox="0 0 800 650" shapeRendering="crispEdges">
        {FIELD_PLANTS.map(({ crop, x, y }, index) => (
          <g key={index} transform={`translate(${x} ${y})`}>
            <CropShapes crop={crop} />
          </g>
        ))}
      </svg>
    </div>
  );
}

export function WelcomeStep({ futures, onStart }: { futures: number; onStart: () => void }) {
  const [explaining, setExplaining] = useState(false);
  return (
    <main className="welcome">
      <PixelCropField />
      <div className="welcome-shell">
        <header className="welcome-header">
          <span className="welcome-brand">
            <svg viewBox="0 0 28 28" aria-hidden="true">
              <path d="M3 3h10v10H3zM15 3h10v4H15zM15 9h10v4H15zM3 15h4v10H3zM9 15h16v4H9zM9 21h16v4H9z" fill="currentColor" />
            </svg>
            <strong>Field Shift</strong>
          </span>
          <span className="welcome-header-note">Climate-smart crop planning</span>
        </header>
        <section className="welcome-hero" aria-labelledby="welcome-title">
          <div className="welcome-copy">
            <p className="kicker">Welcome to Field Shift</p>
            <h1 id="welcome-title">Build a five-year crop plan for a changing climate.</h1>
            <p className="welcome-lead">Explore crop rotations that balance financial return, soil health, and water—guided by NASA climate data, local field conditions, and your priorities.</p>
            <div className="welcome-actions">
              <button className="primary welcome-start" type="button" onClick={onStart}>Start planning <span aria-hidden="true">→</span></button>
              <p className="welcome-start-note">Three simple steps. No account needed.</p>
            </div>
            <p className="welcome-data">NASA climate data <span aria-hidden="true">·</span> Local soil and crop data <span aria-hidden="true">·</span> Your priorities</p>
            <button className="method-trigger" type="button" aria-haspopup="dialog" onClick={() => setExplaining(true)}>
              <span className="method-question" aria-hidden="true">?</span><span>See how the estimates are calculated</span><span aria-hidden="true">→</span>
            </button>
          </div>
          <aside className="welcome-guide" aria-label="What to expect">
            <p className="kicker">What to expect</p>
            <h2>From your field to a practical plan.</h2>
            <ol className="welcome-steps">
              <li><span aria-hidden="true">1</span><div><strong>Choose your place and crop</strong><p>Select your municipality and tell us what is growing now.</p></div></li>
              <li><span aria-hidden="true">2</span><div><strong>Set what matters to you</strong><p>Balance income, soil health, and water according to your priorities.</p></div></li>
              <li><span aria-hidden="true">3</span><div><strong>Compare your five-year options</strong><p>Explore crop sequences, estimated returns, and possible changes in soil and water.</p></div></li>
            </ol>
          </aside>
        </section>
        <p className="welcome-footnote">Explore possibilities and compare trade-offs. Results are estimates, not agronomic recommendations or guarantees.</p>
      </div>
      <MethodDialog open={explaining} onClose={() => setExplaining(false)} facts={null} futures={futures} />
    </main>
  );
}
