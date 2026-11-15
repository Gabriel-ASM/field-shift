import assert from "node:assert/strict";
import { test } from "node:test";
import { CARDS, shuffled } from "../src/microlearning.ts";

test("the wait cards are a random permutation: every card once, and the input is untouched", () => {
  const before = [...CARDS];
  const order = shuffled(CARDS, () => 0.5);
  assert.equal(order.length, CARDS.length);
  const byTitle = (a: { title: string }, b: { title: string }) => a.title.localeCompare(b.title);
  assert.deepEqual([...order].sort(byTitle), [...CARDS].sort(byTitle));
  assert.deepEqual([...CARDS], before);
  assert.notDeepEqual(shuffled(CARDS, () => 0.01), shuffled(CARDS, () => 0.99), "different draws give different orders");
});
