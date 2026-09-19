import { test, expect, tcId, liveReady, liveSkipReason, storageStatePath } from "./fixtures";

/**
 * Four merchant portal jobs — nav/module expectations from merchant-nav.ts.
 * Live UI asserts require MERCHANT_E2E_LIVE=1 + existing Clerk storage jar for that seat.
 */

type Job = "owner" | "dispatcher" | "accounting" | "viewer";

const PERSONA_MODULES: Record<Job, string[]> = {
  owner: [
    "dashboard",
    "book",
    "routes",
    "orders",
    "tracking",
    "support",
    "billing",
    "reports",
    "api_keys",
    "users",
    "settings",
    "claims",
  ],
  dispatcher: ["dashboard", "book", "routes", "orders", "tracking", "claims", "support"],
  accounting: ["dashboard", "orders", "tracking", "billing", "reports", "claims", "support"],
  viewer: ["dashboard", "orders", "tracking", "support"],
};

const MUST_SEE: Record<Job, string[]> = {
  owner: ["/book", "/billing", "/api", "/team", "/settings"],
  dispatcher: ["/book", "/routes", "/orders"],
  accounting: ["/billing", "/reports"],
  viewer: ["/dashboard", "/orders", "/track"],
};

const MUST_HIDE: Record<Job, string[]> = {
  owner: [],
  dispatcher: ["/billing", "/api", "/team", "/settings"],
  accounting: ["/book", "/routes", "/api", "/team"],
  viewer: ["/book", "/billing", "/api", "/team", "/settings", "/reports", "/routes"],
};

function hrefsForModules(modules: string[]): string[] {
  const nav: Record<string, string> = {
    "/dashboard": "dashboard",
    "/book": "book",
    "/routes": "routes",
    "/orders": "orders",
    "/track": "tracking",
    "/help": "support",
    "/billing": "billing",
    "/reports": "reports",
    "/notifications": "support",
    "/api": "api_keys",
    "/shopify": "api_keys",
    "/team": "users",
    "/referrals": "settings",
    "/settings": "settings",
  };
  const allowed = new Set(modules);
  return Object.entries(nav)
    .filter(([, mod]) => allowed.has(mod))
    .map(([href]) => href);
}

const emptyState = { cookies: [] as [], origins: [] as [] };

for (const job of Object.keys(PERSONA_MODULES) as Job[]) {
  test.describe(`persona ${job} ${tcId(`MP-JOB-${job.toUpperCase()}`)} @p0`, () => {
    test(`module→nav contract for ${job}`, async () => {
      const hrefs = hrefsForModules(PERSONA_MODULES[job]);
      for (const route of MUST_SEE[job]) {
        expect(hrefs, `${job} should see ${route}`).toContain(route);
      }
      for (const route of MUST_HIDE[job]) {
        expect(hrefs, `${job} should hide ${route}`).not.toContain(route);
      }
    });

    if (job === "dispatcher" || job === "viewer") {
      test.describe(`live UI ${job}`, () => {
        const ready = liveReady(job);
        test.skip(!ready, liveSkipReason(job));
        test.use({ storageState: storageStatePath(job) || emptyState });

        test(`live UI nav for ${job}`, async ({ page }) => {
          await page.goto("/dashboard");
          await expect(page.locator("body")).toBeVisible();
          for (const route of MUST_SEE[job]) {
            const link = page.locator(`a[href="${route}"], a[href^="${route}?"]`).first();
            await expect(link).toBeVisible({ timeout: 15_000 });
          }
          for (const route of MUST_HIDE[job]) {
            const link = page.locator(`nav a[href="${route}"]`);
            await expect(link).toHaveCount(0);
          }
        });
      });
    }
  });
}
