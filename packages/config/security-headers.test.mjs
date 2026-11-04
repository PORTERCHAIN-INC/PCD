/** Run: node --test packages/config/security-headers.test.mjs */
import assert from "node:assert/strict";
import { describe, it } from "node:test";
import { portalCsp, websiteCsp } from "./security-headers.mjs";

const dir = (csp, name) => csp.split("; ").find((d) => d.startsWith(name + " ")) ?? "";

describe("Keycloak CSP (no Clerk)", () => {
  for (const [label, csp] of [
    ["website", websiteCsp({})],
    ["merchant", portalCsp({ app: "merchant" })],
    ["customer", portalCsp({ app: "customer" })],
    ["driver", portalCsp({ app: "driver" })],
    ["admin", portalCsp({ app: "admin" })],
  ]) {
    it(`${label} posts forms only to self + Keycloak and has no Clerk hosts`, () => {
      assert.match(dir(csp, "form-action"), /'self' https:\/\/auth\.porterchain\.com/);
      assert.doesNotMatch(csp, /clerk/i);
      assert.match(dir(csp, "img-src"), /https:/);
      assert.match(dir(csp, "worker-src"), /'self' blob:/);
      assert.match(dir(csp, "style-src"), /'unsafe-inline'/);
    });
  }
});

describe("GlitchTip CSP (no sentry.io)", () => {
  const dsn = "https://abc123@errors.example.test/2";
  it("adds only the GlitchTip DSN origin to connect-src", () => {
    for (const csp of [
      websiteCsp({ errorsDsn: dsn }),
      portalCsp({ app: "admin", errorsDsn: dsn }),
    ]) {
      assert.match(dir(csp, "connect-src"), /https:\/\/errors\.example\.test(\s|$)/);
      assert.doesNotMatch(csp, /sentry\.io/);
      assert.doesNotMatch(csp, /abc123/);
    }
  });
  it("adds nothing when the DSN is unset", () => {
    assert.doesNotMatch(dir(portalCsp({ app: "driver" }), "connect-src"), /errors\.example/);
  });
});

describe("plain-http local stack", () => {
  it("skips upgrade-insecure-requests on http origins; https/prod keeps it", () => {
    assert.ok(!portalCsp({ app: "admin", plainHttp: true }).includes("upgrade-insecure-requests"));
    assert.ok(portalCsp({ app: "admin" }).includes("upgrade-insecure-requests"));
  });
});

it("portal CSP allows the API websocket origin (ws for http, wss for https)", () => {
  const a = portalCsp({ app: "admin", apiUrl: "http://192.168.2.103:58001" });
  assert.match(a, /connect-src[^;]*ws:\/\/192\.168\.2\.103:58001/);
  const b = portalCsp({ app: "admin", apiUrl: "https://api.porterchain.com" });
  assert.match(b, /connect-src[^;]*wss:\/\/api\.porterchain\.com/);
});
