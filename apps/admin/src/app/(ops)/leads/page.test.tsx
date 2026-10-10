import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { navigationState } from "@/test/navigation-state";
import { mockAdminAuth, renderWithProviders, sampleLead } from "@/test/render";

const list = vi.fn();
const metrics = vi.fn();
const referralCredits = vi.fn();
const speed = vi.fn();
const weeklySummary = vi.fn();

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
      speed: (...args: unknown[]) => speed(...args),
      weeklySummary: (...args: unknown[]) => weeklySummary(...args),
    },
  };
});

import LeadsListClient from "@/components/leads/LeadsListClient";

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
    const win = (days: number) => ({
      days,
      leads: 10,
      answered: 8,
      median_first_reply_minutes: 4.2,
      answered_within_5m_pct: 62.5,
      quoted: 4,
      quote_to_booking_pct: 50,
      booked: 2,
      booking_to_repeat_pct: 50,
      win_rate_by_channel: [{ channel: "whatsapp", leads: 4, won: 2, lost: 1, win_rate: 66.7 }],
    });
    speed.mockResolvedValue({ generated_at: new Date().toISOString(), windows: [win(7), win(30)] });
    weeklySummary.mockResolvedValue({
      won: 2,
      lost: 1,
      win_rate: 66.7,
      by_channel: [],
      lost_reasons: [{ reason: "price", count: 1 }],
    });
  });

  it("shows the speed strip first: median reply, answered < 5 min, win rate by channel", async () => {
    renderWithProviders(<LeadsListClient />);
    const strip = await screen.findByRole("region", { name: /lead speed/i });
    expect(await screen.findByText("4.2m")).toBeInTheDocument();
    expect(screen.getByText("63%")).toBeInTheDocument();
    expect(strip).toHaveTextContent(/win rate by channel/i);
    expect(await screen.findByText(/top loss reason/i)).toBeInTheDocument();
  });

  it("supports keyboard triage (j, /)", async () => {
    const user = userEvent.setup();
    renderWithProviders(<LeadsListClient />);
    await screen.findAllByText("Acme Logistics");
    await user.keyboard("/");
    expect(screen.getByRole("searchbox", { name: /search leads/i })).toHaveFocus();
  });

  it("renders lead workspace heading, metrics strip, and lead row", async () => {
    renderWithProviders(<LeadsListClient />);

    expect(await screen.findByRole("heading", { name: /^inbox$/i })).toBeInTheDocument();
    await waitFor(() => expect(list).toHaveBeenCalled());
    expect((await screen.findAllByText("Acme Logistics"))[0]).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /add lead/i })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /merge candidate queue/i })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /sla-breached leads/i })).toBeInTheDocument();
  });

  it("opens manual capture controls", async () => {
    const user = userEvent.setup();
    renderWithProviders(<LeadsListClient />);
    await screen.findByRole("heading", { name: /^inbox$/i });
    await user.click(screen.getByRole("button", { name: /add lead/i }));
    expect(
      await screen.findByRole("heading", { name: /manual lead capture/i })
    ).toBeInTheDocument();
    expect(screen.getByText(/^company$/i)).toBeInTheDocument();
  });

  it("opens on the Now tab with Now / Waiting / All views (drivers excluded)", async () => {
    const user = userEvent.setup();
    renderWithProviders(<LeadsListClient />);
    await screen.findAllByText("Acme Logistics");
    const firstFilters = list.mock.calls[0]?.[1] as { view?: string };
    expect(firstFilters?.view).toBe("now");
    expect(screen.getByRole("tab", { name: "Now" })).toHaveAttribute("aria-selected", "true");
    await user.click(screen.getByRole("tab", { name: "Waiting" }));
    await waitFor(() =>
      expect((list.mock.calls.at(-1)?.[1] as { view?: string }).view).toBe("waiting")
    );
    expect(screen.getByRole("button", { name: /^driver applicants$/i })).toBeInTheDocument();
  });

  it("row shows channel icon, calm waiting time (red when over 5m) and score", async () => {
    list.mockResolvedValue({
      items: [
        sampleLead({
          channel: "whatsapp",
          awaiting_reply: true,
          sla_first_response_due_at: new Date(Date.now() - 20 * 60_000).toISOString(),
        }),
      ],
      total: 1,
      limit: 50,
      offset: 0,
    });
    renderWithProviders(<LeadsListClient />);
    await screen.findAllByText("Acme Logistics");
    expect(screen.getAllByText("WhatsApp").length).toBeGreaterThan(0); // icon label
    const wait = screen.getByTitle("Over the 5-minute reply target");
    expect(wait.textContent).toMatch(/^\d+(m|h \d+m|d)$/);
    expect(wait.className).toContain("text-red-700");
    expect(screen.getByTitle("Fit score")).toBeInTheDocument();
  });

  it("shows bulk actions when rows are selected", async () => {
    const user = userEvent.setup();
    renderWithProviders(<LeadsListClient />);
    await screen.findAllByText("Acme Logistics");
    await user.click(screen.getByRole("checkbox", { name: /select acme logistics/i }));
    expect(await screen.findByRole("region", { name: /bulk actions/i })).toBeInTheDocument();
    expect(screen.getByText("1 selected")).toBeInTheDocument();
  });

  it("toggles merge queue filter and refetches", async () => {
    const user = userEvent.setup();
    renderWithProviders(<LeadsListClient />);
    await screen.findAllByText("Acme Logistics");
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
    renderWithProviders(<LeadsListClient />);
    expect(await screen.findByRole("heading", { name: /driver applicants/i })).toBeInTheDocument();
    expect(await screen.findByText(/vehicle partner applications/i)).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: /add lead/i })).not.toBeInTheDocument();
    expect((await screen.findAllByText("Driver Partner Co"))[0]).toBeInTheDocument();
  });
});
