import assert from "node:assert/strict";
import { hasClerkSessionHint, type CookieReader } from "./clerkEdgeSession";

function jar(entries: Record<string, string>): CookieReader {
  const map = new Map(Object.entries(entries));
  return {
    get: (name) => {
      const value = map.get(name);
      return value === undefined ? undefined : { value };
    },
    getAll: () => [...map.entries()].map(([name, value]) => ({ name, value })),
  };
}

assert.equal(hasClerkSessionHint(jar({})), false);
assert.equal(hasClerkSessionHint(jar({ __client_uat: "0" })), false);
assert.equal(hasClerkSessionHint(jar({ __client_uat: "1710000000" })), true);
assert.equal(hasClerkSessionHint(jar({ __session: "eyJhbGciOiJIUzI1NiJ9.e30.sig" })), true);
assert.equal(
  hasClerkSessionHint(jar({ clerk_foo__client_uat: "1710000000" })),
  true,
  "prefixed __client_uat"
);
assert.equal(hasClerkSessionHint(jar({ clerk_foo__client_uat: "0" })), false);

console.log("clerkEdgeSession ok");
