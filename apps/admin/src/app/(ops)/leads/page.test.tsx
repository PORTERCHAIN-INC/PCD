import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { navigationState } from "@/test/navigation-state";
import { mockAdminAuth, renderWithProviders, sampleLead } from "@/test/render";

const list = vi.fn();
const metrics = vi.fn();
const referralCredits = vi.fn();

vi.mock("@/hooks/useAdminAuth", () => ({
  useAdminAuth: () => mockAdminAuth(),
}));

vi.mock("@/lib/leads", async () => {
  const actual = await vi.importActual<typeof import("@/lib/leads")>("@/lib/leads");
  return {
    ...actual,
    leadsApi: {
      ...actual.leadsApi,
      list: (...args: unknown[]) => list(...args),
      metrics: (...args: unknown[]) => metrics(...args),
      referralCredits: (...args: unknown[]) => referralCredits(...args),
    },
  };
});

import LeadsPage from "./page";

describe("LeadsPage (merchant inbox)", () => {
  beforeEach(() => {
    navigationState.pathname = "/leads";
    navigationState.search = "";
    list.mockReset();
    metrics.mockReset();
    referralCredits.mockReset();
    list.mockResolvedValue({
      items: [sampleLead()],
      total: 1,
      limit: 50,
      offset: 0,
    });
    metrics.mockResolvedValue({
      window_days: 30,
      ingest: { total: 12, by_channel: { website: 8 } },
      leads: {
        total: 10,
        converted: 2,
        conversion_rate: 20,
        merge_candidates: 1,
        soft_duplicate_rate_pct: 10,
      },
      sla: { open_new_with_due: 3, breached_new: 1, median_first_touch_minutes: 45 },
      capi: {
        meta_lead_id_leads: 2,
        meta_family_leads_window: 4,
        meta_lead_id_coverage_pct: 50,
      },
      assist: { nim_calls: 1 },
    });
    referralCredits.mockResolvedValue([]);
  });

  it("renders lead workspace heading, metrics strip, and lead row", async () => {
    renderWithProviders(<LeadsPage />);

    expect(await screen.findByRole("heading", { name: /lead workspace/i })).toBeInTheDocument();
    await waitFor(() => expect(list).toHaveBeenCalled());
    expect(await screen.findByText("Acme Logistics")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /add lead/i })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /merge candidate queue/i })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /sla-breached leads/i })).toBeInTheDocument();
  });

  it("opens manual capture controls", async () => {
    const user = userEvent.setup();
    renderWithProviders(<LeadsPage />);
    await screen.findByRole("heading", { name: /lead workspace/i });
    await user.click(screen.getByRole("button", { name: /add lead/i }));
    expect(
      await screen.findByRole("heading", { name: /manual lead capture/i })
    ).toBeInTheDocument();
    expect(screen.getByText(/^company$/i)).toBeInTheDocument();
  });

  it("toggles merge queue filter and refetches", async () => {
    const user = userEvent.setup();
    renderWithProviders(<LeadsPage />);
    await screen.findByText("Acme Logistics");
    const before = list.mock.calls.length;
    await user.click(screen.getByRole("button", { name: /merge candidate queue/i }));
    await waitFor(() => expect(list.mock.calls.length).toBeGreaterThan(before));
    const lastFilters = list.mock.calls.at(-1)?.[1] as { merge_candidates?: boolean };
    expect(lastFilters?.merge_candidates).toBe(true);
  });
});

describe("LeadsPage (driver applications)", () => {
  beforeEach(() => {
    navigationState.pathname = "/leads";
    navigationState.search = "source=website_driver_partner";
    list.mockReset();
    metrics.mockReset();
    referralCredits.mockReset();
    list.mockResolvedValue({
      items: [
        sampleLead({
          source: "website_driver_partner",
          intent_type: "driver_partner",
          company_name: "Driver Partner Co",
        }),
      ],
      total: 1,
      limit: 50,
      offset: 0,
    });
    referralCredits.mockResolvedValue([]);
  });

  it("switches copy and hides merchant-only capture when driver filter is on", async () => {
    renderWithProviders(<LeadsPage />);
    expect(await screen.findByRole("heading", { name: /lead workspace/i })).toBeInTheDocument();
    expect(await screen.findByText(/vehicle partner applications/i)).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /add lead/i })).not.toBeInTheDocument();
    expect(await screen.findByText("Driver Partner Co")).toBeInTheDocument();
  });
});
