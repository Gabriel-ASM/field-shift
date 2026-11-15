import assert from "node:assert/strict";
import { test } from "node:test";
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
