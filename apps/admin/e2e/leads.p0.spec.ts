/**
 * Admin Leads P0 — Playwright with network stubs (no live API required).
 * SSOT: docs/testing/admin_p0_registry.json UI-LEAD-*
 *
 * Run: pnpm --filter @porterchain/admin test:e2e:leads
 * Auth: global storageState from fixtures (ADMIN_STORAGE_STATE | ADMIN_STAFF_SID | bypass).
 * Live: ADMIN_RUN_LIVE=1 fails hard if admin on ADMIN_BASE_URL is down.
 */
import { test, expect, tcId, ensureAdminReachable } from "./fixtures";

const LEAD_ROW = {
  id: "lead-e2e-1",
  company_name: "E2E Acme Logistics",
  industry: "food",
  website: null,
  business_type: null,
  address: { city: "Toronto", province: "ON" },
  primary_contact_name: "Eve Two",
  phone: "+14165550101",
  email: "eve@acme.test",
  estimated_deliveries_per_month: 80,
  estimated_revenue_cents: 180000,
  preferred_vehicle: null,
  service_area: "GTA",
  current_logistics_provider: null,
  source: "website_contact",
  channel: "website",
  intent_type: "merchant",
  decision_status: "new",
  status: "new",
  priority: "high",
  assigned_to: null,
  expected_close_date: null,
  tags: [],
  internal_notes: "Stubbed lead",
  lead_score: 55,
  company_id: null,
  deal_id: null,
  contact_id: null,
  referred_by_merchant_id: null,
  merge_candidate_of: null,
  sla_first_response_due_at: null,
  last_touch_at: null,
  consent: {},
  custom_fields: {},
  created_at: "2026-09-17T12:00:00.000Z",
  updated_at: "2026-09-17T12:00:00.000Z",
};

const METRICS = {
  window_days: 30,
  ingest: { total: 3, by_channel: { website: 3 } },
  leads: {
    total: 3,
    converted: 1,
    conversion_rate: 33.3,
    merge_candidates: 0,
    soft_duplicate_rate_pct: 0,
  },
  sla: { open_new_with_due: 1, breached_new: 0, median_first_touch_minutes: 20 },
  capi: {
    meta_lead_id_leads: 0,
    meta_family_leads_window: 0,
    meta_lead_id_coverage_pct: null,
  },
  assist: { nim_calls: 0 },
};

/** Stub BFF (`/api/porterchain/v1/...`) and any direct API host. */
async function stubLeadsApi(page: import("@playwright/test").Page) {
  await page.route("**/v1/admin/leads/metrics**", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify(METRICS),
    });
  });
  await page.route("**/v1/admin/leads/pipeline**", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify([
        {
          stage: "prospecting",
          cards: [
            {
              type: "lead",
              id: LEAD_ROW.id,
              title: LEAD_ROW.company_name,
              company_name: LEAD_ROW.company_name,
              value_cents: LEAD_ROW.estimated_revenue_cents,
              secondary: null,
              channel: "website",
              score: 55,
            },
          ],
          count: 1,
          value_cents: LEAD_ROW.estimated_revenue_cents,
          hidden: 0,
          lead_count: 1,
          deal_count: 0,
        },
      ]),
    });
  });
  await page.route("**/v1/admin/leads/calendar**", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify([]),
    });
  });
  await page.route("**/v1/admin/leads/referral-credits**", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify([]),
    });
  });
  await page.route("**/v1/admin/leads?**", async (route) => {
    const url = new URL(route.request().url());
    const source = url.searchParams.get("source");
    const rows =
      source === "website_driver_partner"
        ? [
            {
              ...LEAD_ROW,
              id: "driver-lead-1",
              company_name: "Driver Applicant Co",
              source: "website_driver_partner",
              intent_type: "driver_partner",
            },
          ]
        : [LEAD_ROW];
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify(rows),
    });
  });
  await page.route("**/v1/admin/leads", async (route) => {
    if (route.request().method() === "GET") {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify([LEAD_ROW]),
      });
      return;
    }
    await route.continue();
  });
}

test.describe(`UI-LEAD-001 ${tcId("UI-LEAD-001")} @p0`, () => {
  test("merchant inbox vs driver applications filter", async ({ page }) => {
    await ensureAdminReachable(page);
    await stubLeadsApi(page);
    await page.goto("/leads");
    await expect(page.getByRole("heading", { name: /merchant leads/i })).toBeVisible({
      timeout: 15_000,
    });
    await expect(page.getByText("E2E Acme Logistics")).toBeVisible();

    await page.goto("/leads?source=website_driver_partner");
    await expect(page.getByRole("heading", { name: /driver applications/i })).toBeVisible();
    await expect(page.getByText("Driver Applicant Co")).toBeVisible();
  });
});

test.describe(`UI-LEAD-002 ${tcId("UI-LEAD-002")} @p0`, () => {
  test("pipeline stages load", async ({ page }) => {
    await ensureAdminReachable(page);
    await stubLeadsApi(page);
    await page.goto("/leads/pipeline");
    await expect(page.getByRole("heading", { name: /acquisition pipeline/i })).toBeVisible({
      timeout: 15_000,
    });
    await expect(page.getByText(/prospecting/i)).toBeVisible();
    await expect(page.getByText("E2E Acme Logistics")).toBeVisible();
  });
});

test.describe(`UI-LEAD-003 ${tcId("UI-LEAD-003")} @p0`, () => {
  test("sales calendar page mounts", async ({ page }) => {
    await ensureAdminReachable(page);
    await stubLeadsApi(page);
    await page.goto("/leads/calendar");
    await expect(page.locator("body")).toBeVisible();
    await expect(page.getByRole("link", { name: /back to leads/i })).toBeVisible({
      timeout: 15_000,
    });
  });
});
