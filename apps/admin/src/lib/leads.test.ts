import { beforeEach, describe, expect, it, vi } from "vitest";

const adminFetch = vi.fn();

vi.mock("@/lib/api", () => ({
  adminFetch: (...args: unknown[]) => adminFetch(...args),
}));

import {
  LEAD_CHANNELS,
  LEAD_DECISION_STATUSES,
  LEAD_INTENT_TYPES,
  LEAD_PRIORITIES,
  LEAD_SOURCES,
  LEAD_STATUSES,
  buildLeadFiltersQuery,
  leadForm,
  leadIntent,
  leadMessage,
  leadsApi,
  DECISION_TONES,
  PRIORITY_TONES,
  STATUS_TONES,
} from "@/lib/leads";
import { sampleLead } from "@/test/render";

describe("buildLeadFiltersQuery", () => {
  it("returns empty string with no filters", () => {
    expect(buildLeadFiltersQuery({})).toBe("");
  });

  it("encodes enum + boolean filters for the inbox", () => {
    const q = buildLeadFiltersQuery({
      status: "new",
      channel: "whatsapp",
      unassigned: true,
      merge_candidates: true,
      sla_breached: true,
      search: "Acme GTA",
    });
    const params = new URLSearchParams(q.slice(1));
    expect(params.get("status")).toBe("new");
    expect(params.get("channel")).toBe("whatsapp");
    expect(params.get("unassigned")).toBe("true");
    expect(params.get("merge_candidates")).toBe("true");
    expect(params.get("sla_breached")).toBe("true");
    expect(params.get("search")).toBe("Acme GTA");
  });
});

describe("lead field helpers", () => {
  it("reads intent/form/message from custom_fields with notes fallback", () => {
    const lead = sampleLead() as Parameters<typeof leadIntent>[0];
    expect(leadIntent(lead)).toBe("quote");
    expect(leadForm(lead)).toBe("website_contact");
    expect(leadMessage(lead)).toBe("Capacity for cold chain");

    const notesOnly = sampleLead({
      custom_fields: {},
      internal_notes: "Call back Friday",
    }) as Parameters<typeof leadMessage>[0];
    expect(leadMessage(notesOnly)).toBe("Call back Friday");
  });
});

describe("enum + tone contracts", () => {
  it("keeps funnel enums non-empty and tone maps aligned", () => {
    expect(LEAD_STATUSES.length).toBeGreaterThan(0);
    expect(LEAD_PRIORITIES).toContain("urgent");
    expect(LEAD_CHANNELS).toContain("merchant_referral");
    expect(LEAD_INTENT_TYPES).toContain("driver_partner");
    expect(LEAD_DECISION_STATUSES).toContain("ready_to_convert");
    expect(LEAD_SOURCES).toContain("website_driver_partner");

    for (const status of LEAD_STATUSES) {
      expect(STATUS_TONES[status]).toBeTruthy();
    }
    for (const priority of LEAD_PRIORITIES) {
      expect(PRIORITY_TONES[priority]).toBeTruthy();
    }
    for (const decision of LEAD_DECISION_STATUSES) {
      expect(DECISION_TONES[decision]).toBeTruthy();
    }
  });
});

describe("leadsApi", () => {
  beforeEach(() => {
    adminFetch.mockReset();
  });

  it("list hits filtered admin endpoint and zod-parses page envelope", async () => {
    adminFetch.mockResolvedValueOnce({
      items: [sampleLead()],
      total: 1,
      limit: 50,
      offset: 0,
    });
    const page = await leadsApi.list("tok", { channel: "website", status: "new" });
    expect(adminFetch).toHaveBeenCalledWith("/v1/admin/leads?status=new&channel=website", "tok");
    expect(page.items[0]?.company_name).toBe("Acme Logistics");
    expect(page.total).toBe(1);
  });

  it("rejects malformed list payloads", async () => {
    adminFetch.mockResolvedValueOnce({ items: [{ id: "x" }], total: 1, limit: 50, offset: 0 });
    await expect(leadsApi.list("tok")).rejects.toThrow();
  });

  it("metrics / pipeline / calendar / detail use correct paths", async () => {
    adminFetch.mockResolvedValueOnce({
      window_days: 30,
      ingest: { total: 1, by_channel: {} },
      leads: {
        total: 1,
        converted: 0,
        conversion_rate: 0,
        merge_candidates: 0,
        soft_duplicate_rate_pct: 0,
      },
      sla: { open_new_with_due: 0, breached_new: 0, median_first_touch_minutes: null },
      capi: {
        meta_lead_id_leads: 0,
        meta_family_leads_window: 0,
        meta_lead_id_coverage_pct: null,
      },
      assist: { nim_calls: 0 },
    });
    await leadsApi.metrics("tok", 30);
    expect(adminFetch).toHaveBeenCalledWith("/v1/admin/leads/metrics?days=30", "tok");

    adminFetch.mockResolvedValueOnce([]);
    await leadsApi.pipeline("tok", { search: "Acme", card_type: "lead" });
    expect(adminFetch).toHaveBeenCalledWith(
      "/v1/admin/leads/pipeline?search=Acme&card_type=lead",
      "tok"
    );

    adminFetch.mockResolvedValueOnce([]);
    await leadsApi.calendar("tok", {
      due_after: "2026-09-01T00:00:00.000Z",
      due_before: "2026-09-08T00:00:00.000Z",
    });
    expect(adminFetch.mock.calls.at(-1)?.[0]).toContain("/v1/admin/leads/calendar?");

    adminFetch.mockResolvedValueOnce(sampleLead());
    await leadsApi.detail("tok", "lead-1");
    expect(adminFetch).toHaveBeenCalledWith("/v1/admin/leads/lead-1", "tok");
  });

  it("create / update / convert / assistDecide POST shapes", async () => {
    adminFetch.mockResolvedValueOnce(sampleLead());
    await leadsApi.create("tok", {
      company_name: "New Co",
      email: "n@t.test",
      source: "phone_call",
    });
    expect(adminFetch).toHaveBeenCalledWith(
      "/v1/admin/leads",
      "tok",
      expect.objectContaining({ method: "POST" })
    );

    adminFetch.mockResolvedValueOnce(sampleLead({ status: "contacted" }));
    await leadsApi.update("tok", "lead-1", { status: "contacted" });
    expect(adminFetch).toHaveBeenCalledWith(
      "/v1/admin/leads/lead-1",
      "tok",
      expect.objectContaining({ method: "PATCH" })
    );

    adminFetch.mockResolvedValueOnce({ company_id: "co-1", outcome: "merchant" });
    await leadsApi.convert("tok", "lead-1", { outcome: "merchant", create_deal: true });
    expect(adminFetch).toHaveBeenCalledWith(
      "/v1/admin/leads/lead-1/convert",
      "tok",
      expect.objectContaining({ method: "POST" })
    );

    adminFetch.mockResolvedValueOnce({ ok: true });
    await leadsApi.assistDecide("tok", "lead-1", {
      proposal_id: "p1",
      decision: "reject",
    });
    expect(adminFetch).toHaveBeenCalledWith(
      "/v1/admin/leads/lead-1/assist/decide",
      "tok",
      expect.objectContaining({ method: "POST" })
    );
  });
});
