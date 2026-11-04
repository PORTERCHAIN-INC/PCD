import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { describe, expect, it } from "vitest";

const src = (rel: string) => readFileSync(fileURLToPath(new URL(rel, import.meta.url)), "utf8");

describe("driver /login <-> /onboarding loop guards", () => {
  it("prod compose gives the driver portal a Keycloak session (no Clerk)", () => {
    const compose = src("../../../../infrastructure/deploy/docker-compose.prod.yml");
    const driver = compose.slice(compose.indexOf("container_name: pcd-driver"));
    const env = driver.slice(0, driver.indexOf("expose:"));
    expect(env).toMatch(/KEYCLOAK_URL: \$\{KEYCLOAK_URL/);
    expect(env).toMatch(/AUTH_SESSION_SECRET: \$\{AUTH_SESSION_SECRET:\?/);
    expect(env).not.toMatch(/CLERK_/);
    // build no longer bakes any Clerk publishable key
    expect(src("../../../../.github/workflows/deploy.yml")).not.toMatch(/CLERK_/);
  });

  it("login only redirects out after the server confirms the session", () => {
    const page = src("../app/login/[[...sign-in]]/page.tsx");
    const effect = page.slice(page.indexOf("function KeycloakDriverContinue"));
    const check = effect.indexOf("hasDriverSession()");
    const replace = effect.indexOf("router.replace(redirectUrl)");
    expect(check).toBeGreaterThan(-1);
    expect(replace).toBeGreaterThan(check);
    expect(effect).toMatch(/serverRejected/);
  });
});
