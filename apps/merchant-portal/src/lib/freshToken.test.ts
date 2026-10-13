import assert from "node:assert/strict";
import test from "node:test";

import { withFreshToken } from "./freshToken.ts";

test("every call mints a new token (no stale 60s Clerk JWT)", async () => {
  let n = 0;
  const getToken = async () => `tok-${++n}`;
  const seen: string[] = [];
  const call = async (t: string) => (seen.push(t), t);
  await withFreshToken(getToken, call);
  await withFreshToken(getToken, call);
  assert.deepEqual(seen, ["tok-1", "tok-2"]);
});
