/**
 * BJ — the dev bypass must never ship.
 *
 * Run: node --experimental-strip-types --test packages/auth/src/devBypass.test.ts
 */

import assert from "node:assert/strict";
import { afterEach, describe, it } from "node:test";

import { clerkDevBypassEnabled, clerkDevBypassIgnored, isDevelopmentBuild } from "./devBypass.ts";

const originalNodeEnv = process.env.NODE_ENV;
const originalBypass = process.env.NEXT_PUBLIC_CLERK_DEV_BYPASS;

function build(nodeEnv: string | undefined, bypass: string | undefined) {
  if (nodeEnv === undefined) delete process.env.NODE_ENV;
  else process.env.NODE_ENV = nodeEnv;
  if (bypass === undefined) delete process.env.NEXT_PUBLIC_CLERK_DEV_BYPASS;
  else process.env.NEXT_PUBLIC_CLERK_DEV_BYPASS = bypass;
}

afterEach(() => {
  build(originalNodeEnv, originalBypass);
});

describe("dev bypass never ships", () => {
  it("a production build ignores the variable however it is set", () => {
    for (const value of ["true", "TRUE", "1", "yes"]) {
      build("production", value);
      assert.equal(clerkDevBypassEnabled(), false, `NEXT_PUBLIC_CLERK_DEV_BYPASS=${value}`);
    }
  });

  it("a development build honours the explicit opt-in", () => {
    build("development", "true");
    assert.equal(clerkDevBypassEnabled(), true);
  });

  it("stays off by default even in development", () => {
    build("development", undefined);
    assert.equal(clerkDevBypassEnabled(), false);
    build("development", "false");
    assert.equal(clerkDevBypassEnabled(), false);
  });

  it("only the exact string true opts in", () => {
    for (const value of ["True", "1", "yes", " true"]) {
      build("development", value);
      assert.equal(clerkDevBypassEnabled(), false, `NEXT_PUBLIC_CLERK_DEV_BYPASS=${value}`);
    }
  });

  it("reports when a shipped build is ignoring the variable", () => {
    build("production", "true");
    assert.equal(clerkDevBypassIgnored(), true);
    build("development", "true");
    assert.equal(clerkDevBypassIgnored(), false);
    build("production", undefined);
    assert.equal(clerkDevBypassIgnored(), false);
  });
});

describe("build detection", () => {
  it("only NODE_ENV=production counts as shipped", () => {
    build("production", undefined);
    assert.equal(isDevelopmentBuild(), false);
    for (const value of ["development", "test", undefined]) {
      build(value, undefined);
      assert.equal(isDevelopmentBuild(), true, `NODE_ENV=${value}`);
    }
  });
});
