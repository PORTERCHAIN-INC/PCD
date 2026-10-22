/**
 * Run: node --experimental-strip-types --test packages/auth/src/authTelemetry.test.ts
 */
import assert from "node:assert/strict";
import { describe, it } from "node:test";
import { authTelemetryLogLine, parseAuthEvent, scrubDetail } from "./authTelemetry.ts";

describe("auth telemetry", () => {
  it("drops unknown kinds and junk", () => {
    assert.equal(parseAuthEvent(null), null);
    assert.equal(parseAuthEvent({ kind: "nope" }), null);
  });
  it("never forwards an email address", () => {
    assert.equal(scrubDetail("No account for reviewer@shopify.com"), "No account for [email]");
    const line = authTelemetryLogLine(
      { kind: "clerk_form_error", path: "/sign-in", detail: "Password is incorrect for a@b.co" },
      "merchant",
      "UA"
    );
    assert.ok(line && !line.includes("a@b.co"));
    assert.equal(JSON.parse(line ?? "{}").msg, "auth_client_failure");
  });
  it("caps detail length", () => {
    assert.equal(scrubDetail("x".repeat(500))?.length, 160);
  });
});
