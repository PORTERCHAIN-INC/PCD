/** Run: node --test packages/config/security-headers.test.mjs */
import assert from "node:assert/strict";
import { describe, it } from "node:test";
import { portalCsp, websiteCsp } from "./security-headers.mjs";

const dir = (csp, name) => csp.split("; ").find((d) => d.startsWith(name + " ")) ?? "";

describe("Clerk + Turnstile CSP (Clerk CSP docs)", () => {
  for (const [label, csp] of [
    ["website", websiteCsp({})],
    ["merchant", portalCsp({ app: "merchant" })],
    ["customer", portalCsp({ app: "customer" })],
    ["driver", portalCsp({ app: "driver" })],
  ]) {
    it(`${label} allows Clerk FAPI, Turnstile and protect hosts`, () => {
      for (const d of ["script-src", "frame-src", "connect-src"]) {
        assert.match(dir(csp, d), /https:\/\/challenges\.cloudflare\.com/, `${label} ${d}`);
        assert.match(dir(csp, d), /https:\/\/clerk\.admin\.porterchain\.com/, `${label} ${d}`);
      }
      assert.match(dir(csp, "script-src"), /https:\/\/\*\.protect\.clerk\.com(\s|$)/);
      assert.match(dir(csp, "frame-src"), /https:\/\/\*\.protect\.clerk\.com(\s|$)/);
      assert.match(dir(csp, "connect-src"), /https:\/\/\*\.protect\.clerk\.com:\*/);
      assert.match(dir(csp, "connect-src"), /https:\/\/img\.clerk\.com/);
      assert.match(dir(csp, "img-src"), /https:/);
      assert.match(dir(csp, "worker-src"), /'self' blob:/);
      assert.match(dir(csp, "style-src"), /'unsafe-inline'/);
    });
  }
  it("admin (staff IdP, no Clerk) stays Clerk-free", () => {
    assert.doesNotMatch(portalCsp({ app: "admin" }), /clerk/);
  });
});
