/** One card at a time, in a random order drawn when the analysis starts, changing every few seconds. */

import { useEffect, useState } from "react";
import { CARDS, shuffled } from "../microlearning.ts";

const INTERVAL_MS = 8000;

export function Microlearning() {
  const [order] = useState(() => shuffled(CARDS));
  const [index, setIndex] = useState(0);
  useEffect(() => {
    const timer = window.setInterval(() => setIndex((current) => (current + 1) % order.length), INTERVAL_MS);
    return () => window.clearInterval(timer);
  }, [order]);
  const card = order[index]!;
  return (
    <aside className="micro-card" aria-label="While you wait">
      <span className="micro-count">{index + 1} / {order.length}</span>
      <h3>{card.title}</h3>
      <p key={card.title}>{card.body}</p>
    </aside>
  );
}
