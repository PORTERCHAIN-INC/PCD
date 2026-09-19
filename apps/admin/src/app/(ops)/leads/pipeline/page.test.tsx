import { screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { mockAdminAuth, renderWithProviders } from "@/test/render";

const pipeline = vi.fn();

vi.mock("@/hooks/useAdminAuth", () => ({
  useAdminAuth: () => mockAdminAuth(),
}));

vi.mock("@/lib/leads", async () => {
  const actual = await vi.importActual<typeof import("@/lib/leads")>("@/lib/leads");
  return {
    ...actual,
    leadsApi: {
      ...actual.leadsApi,
      pipeline: (...args: unknown[]) => pipeline(...args),
    },
  };
});

import LeadsPipelinePage from "./page";

describe("LeadsPipelinePage", () => {
  beforeEach(() => {
    pipeline.mockReset();
    pipeline.mockResolvedValue([
      {
        stage: "prospecting",
        cards: [
          {
            type: "lead",
            id: "lead-1",
            title: "Acme Logistics",
            company_name: "Acme Logistics",
            value_cents: 250000,
            secondary: "score 42",
            channel: "website",
            score: 42,
          },
        ],
        count: 1,
        value_cents: 250000,
        hidden: 0,
        lead_count: 1,
        deal_count: 0,
      },
      {
        stage: "qualified",
        cards: [],
        count: 0,
        value_cents: 0,
        hidden: 0,
        lead_count: 0,
        deal_count: 0,
      },
    ]);
  });

  it("loads acquisition pipeline columns and lead cards", async () => {
    renderWithProviders(<LeadsPipelinePage />);
    expect(
      await screen.findByRole("heading", { name: /acquisition pipeline/i })
    ).toBeInTheDocument();
    await waitFor(() => expect(pipeline).toHaveBeenCalled());
    expect(screen.getByText(/prospecting/i)).toBeInTheDocument();
    expect(screen.getByText("Acme Logistics")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /back to inbox/i })).toHaveAttribute("href", "/leads");
  });
});
