import { RELOAD_MESSAGE } from "../version.ts";

/** The API was redeployed with another build: this page's code may misread its answers, so it only offers a reload. */
export function Outdated() {
  return (
    <section className="outdated" role="alert">
      <h2>{RELOAD_MESSAGE}</h2>
      <div className="actions"><button type="button" className="primary" onClick={() => window.location.reload()}>Reload</button></div>
    </section>
  );
}
