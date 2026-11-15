import assert from "node:assert/strict";
import { test } from "node:test";
import { wellFormed } from "../src/resultShape.ts";
import type { RunResult } from "../src/types.ts";
import { BUNDLE_VERSION, outdated } from "../src/version.ts";

test("a bundle built outside the image is dev", () => {
  assert.equal(BUNDLE_VERSION, "dev");
});

test("only two known, different builds are out of date", () => {
  assert.equal(outdated("abc1234", "def5678"), true);
  assert.equal(outdated("abc1234", "abc1234"), false);
  assert.equal(outdated("dev", "def5678"), false);
  assert.equal(outdated("abc1234", "dev"), false);
  assert.equal(outdated("abc1234", undefined), false);   // an API older than the check
  assert.equal(outdated("abc1234", null), false);
});

const VALUE = { mean: 1, p5: 0, p50: 1, p95: 2, cvar5: -1, count: 300 };
const ROUTE = { crops: ["soybean", "maize_grain"], value: VALUE };

function result(scenario: Record<string, unknown>, ranking: unknown = { support: { minimum_ranked: 2 } }): RunResult {
  return { ranking, scenarios: [scenario] } as unknown as RunResult;
}

test("a result with routes, values and a ranking reference is well formed, even when nothing is priced", () => {
  assert.equal(wellFormed(result({ routes: [ROUTE], ranking_reference: { cvar5: -1, p95: 2, count: 300, routes: 1 } })), true);
  assert.equal(wellFormed(result({ routes: [{ ...ROUTE, value: null }], ranking_reference: null })), true);
  assert.equal(wellFormed(result({ routes: [], ranking_reference: null })), true);
});

test("a result missing the fields the screen reads is malformed, not unpriced", () => {
  assert.equal(wellFormed(result({ routes: [{ crops: ["soybean"] }], ranking_reference: null })), false);       // `value` absent
  assert.equal(wellFormed(result({ routes: [ROUTE] })), false);                                                // no ranking_reference
  assert.equal(wellFormed(result({ routes: [{ ...ROUTE, value: { p50: 1 } }], ranking_reference: null })), false);
  assert.equal(wellFormed(result({ overall: {}, ranking_reference: null })), false);                           // no routes
  assert.equal(wellFormed(result({ routes: [ROUTE], ranking_reference: null }, null)), false);                 // no ranking settings
  assert.equal(wellFormed({ scenarios: [] } as unknown as RunResult), false);
});
