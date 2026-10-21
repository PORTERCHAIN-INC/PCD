import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { describe, expect, it } from "vitest";

const src = (rel: string) => readFileSync(fileURLToPath(new URL(rel, import.meta.url)), "utf8");

describe("driver /login <-> /onboarding loop guards", () => {
  it("prod compose gives the driver portal the Driver-instance Clerk secret", () => {
    const compose = src("../../../../infrastructure/deploy/docker-compose.prod.yml");
    const driver = compose.slice(compose.indexOf("container_name: pcd-driver"));
    const env = driver.slice(0, driver.indexOf("expose:"));
    expect(env).toMatch(/CLERK_SECRET_KEY: \$\{CLERK_DRIVER_SECRET_KEY:\?/);
    // build uses the Driver publishable key; keep the pair aligned
    expect(src("../../../../.github/workflows/deploy.yml")).toMatch(
      /matrix\.id == 'driver' && secrets\.CLERK_DRIVER_PUBLISHABLE_KEY/
    );
  });

  it("login only redirects out after the server confirms the session", () => {
    const page = src("../app/login/[[...sign-in]]/page.tsx");
    const effect = page.slice(page.indexOf("function ClerkDriverContinue"));
    const check = effect.indexOf("hasDriverSession()");
    const replace = effect.indexOf("router.replace(redirectUrl)");
    expect(check).toBeGreaterThan(-1);
    expect(replace).toBeGreaterThan(check);
    expect(effect).toMatch(/serverRejected/);
  });
});
