/** "Behind your estimate": the modal opened by "Wanna know how it was calculated?" (field_shift/front/index.html,
 *  #methodology-dialog). Two tabs: the intuitive version and the decision engine. */

import { useEffect, useRef, useState } from "react";
import { HowItWorks } from "./HowItWorks.tsx";
import { UnderTheHood, type EngineFacts } from "./UnderTheHood.tsx";

const TABS = [
  { id: "simple", number: "01", title: "How it works", note: "The intuitive version" },
  { id: "technical", number: "02", title: "Under the hood", note: "The decision engine" },
] as const;

type Tab = (typeof TABS)[number]["id"];

function Tabs({ current, choose }: { current: Tab; choose: (tab: Tab) => void }) {
  return (
    <div className="method-tabs" role="tablist" aria-label="Explanation detail">
      {TABS.map(({ id, number, title, note }) => (
        <button key={id} className="method-tab" type="button" role="tab" aria-selected={id === current} tabIndex={id === current ? 0 : -1} onClick={() => choose(id)}>
          <span aria-hidden="true">{number}</span><span><strong>{title}</strong><small>{note}</small></span>
        </button>
      ))}
    </div>
  );
}

export function MethodDialog({ open, onClose, facts, futures = 100000 }: { open: boolean; onClose: () => void; facts: EngineFacts | null; futures?: number }) {
  const dialog = useRef<HTMLDialogElement>(null);
  const [tab, setTab] = useState<Tab>("simple");
  useEffect(() => {
    const element = dialog.current;
    if (!element) return;
    if (open && !element.open) element.showModal();
    if (!open && element.open) element.close();
  }, [open]);
  return (
    <dialog ref={dialog} className="method-dialog" aria-labelledby="methodology-title" onClose={onClose}
      onClick={(event) => { if (event.target === dialog.current) onClose(); }}>
      <header className="method-header">
        <div>
          <span className="kicker">Behind your estimate</span>
          <h2 id="methodology-title">A simple answer. A deeper model.</h2>
          <p>Five ideas work together to turn local data into your recommendation.</p>
        </div>
        <button className="method-close" type="button" aria-label="Close explanation" onClick={onClose}>×</button>
      </header>
      {facts && <Tabs current={tab} choose={setTab} />}
      <div className="method-body method-panel" role="tabpanel">
        {tab === "simple" || !facts
          ? <HowItWorks futures={facts?.trajectories ?? futures} years={facts?.model.horizon_years ?? 5} />
          : <UnderTheHood facts={facts} />}
      </div>
    </dialog>
  );
}
