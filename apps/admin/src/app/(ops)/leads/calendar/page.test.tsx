import { screen, waitFor } from "@testing-library/react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { mockAdminAuth, renderWithProviders } from "@/test/render";

const calendar = vi.fn();

vi.mock("@/hooks/useAdminAuth", () => ({
  useAdminAuth: () => mockAdminAuth(),
}));

vi.mock("@/lib/leads", async () => {
  const actual = await vi.importActual<typeof import("@/lib/leads")>("@/lib/leads");
  return {
    ...actual,
    leadsApi: {
      ...actual.leadsApi,
      calendar: (...args: unknown[]) => calendar(...args),
    },
  };
});

import LeadCalendarPage from "./page";

describe("LeadCalendarPage", () => {
  beforeEach(() => {
    calendar.mockReset();
    const due = new Date();
    // Place task mid-week so it lands in the visible Monday–Sunday range.
    const day = due.getDay();
    const mondayOffset = (day + 6) % 7;
    due.setDate(due.getDate() - mondayOffset + 2);
    due.setHours(14, 0, 0, 0);
    calendar.mockResolvedValue([
      {
        id: "task-1",
        title: "Discovery call — Acme",
        task_type: "call",
        status: "open",
        priority: "high",
        entity_type: "lead",
        entity_id: "lead-1",
        due_at: due.toISOString(),
        assigned_to: null,
        created_at: due.toISOString(),
        updated_at: due.toISOString(),
      },
    ]);
  });

  it("fetches calendar tasks for the visible week", async () => {
    renderWithProviders(<LeadCalendarPage />);
    await waitFor(() => expect(calendar).toHaveBeenCalled());
    const args = calendar.mock.calls[0]?.[1] as {
      due_after?: string;
      due_before?: string;
    };
    expect(args.due_after).toBeTruthy();
    expect(args.due_before).toBeTruthy();
    expect(await screen.findByText(/discovery call — acme/i)).toBeInTheDocument();
  });
});
