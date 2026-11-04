import { test } from "node:test";
import assert from "node:assert/strict";
import { cookieSecure } from "./cookieSecure.ts";

test("Secure defaults to production only", () => {
  assert.equal(cookieSecure({ NODE_ENV: "production" } as NodeJS.ProcessEnv), true);
  assert.equal(cookieSecure({ NODE_ENV: "development" } as NodeJS.ProcessEnv), false);
});

test("AUTH_COOKIE_SECURE overrides both ways", () => {
  assert.equal(
    cookieSecure({ NODE_ENV: "production", AUTH_COOKIE_SECURE: "false" } as NodeJS.ProcessEnv),
    false
  );
  assert.equal(
    cookieSecure({ NODE_ENV: "development", AUTH_COOKIE_SECURE: "true" } as NodeJS.ProcessEnv),
    true
  );
});
