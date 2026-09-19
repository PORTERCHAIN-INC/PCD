import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { adminProfileState } from "@/test/admin-profile-state";
import { mockAdminAuth, renderWithProviders, sampleLead } from "@/test/render";

const detail = vi.fn();
const conversations = vi.fn();
const identities = vi.fn();
const assist = vi.fn();
const update = vi.fn();
const convert = vi.fn();
const remove = vi.fn();
const routerPush = vi.fn();

vi.mock("@/hooks/useAdminAuth", () => ({
  useAdminAuth: () => mockAdminAuth(),
}));

vi.mock("@/components/nav/AdminProfileContext", () => ({
  useAdminProfile: () => ({
    profile: {
      get role() {
        return adminProfileState.role;
      },
      get email() {
        return adminProfileState.email;
      },
    },
  }),
}));

vi.mock("@porterchain/auth", () => ({
  hasPermission: (_perms: unknown, key: string) => adminProfileState.permissions.includes(key),
  useOptionalSessionContext: () => ({
    session: {
      get permissions() {
        return adminProfileState.permissions;
      },
    },
  }),
}));

vi.mock("@/components/crm/ActivityTimeline", () => ({
  ActivityTimeline: () => <div data-testid="activity-timeline" />,
}));

vi.mock("@/components/crm/EntityTasks", () => ({
  EntityTasks: () => <div data-testid="entity-tasks" />,
}));

vi.mock("next/navigation", () => ({
  useRouter: () => ({
    push: routerPush,
    replace: vi.fn(),
    back: vi.fn(),
    prefetch: vi.fn(),
  }),
  usePathname: () => "/leads/lead-1",
  useSearchParams: () => new URLSearchParams(),
  useParams: () => ({ id: "lead-1" }),
}));

vi.mock("@/lib/leads", async () => {
  const actual = await vi.importActual<typeof import("@/lib/leads")>("@/lib/leads");
  return {
    ...actual,
    leadsApi: {
      ...actual.leadsApi,
      detail: (...args: unknown[]) => detail(...args),
      conversations: (...args: unknown[]) => conversations(...args),
      identities: (...args: unknown[]) => identities(...args),
      assist: (...args: unknown[]) => assist(...args),
      update: (...args: unknown[]) => update(...args),
      convert: (...args: unknown[]) => convert(...args),
      remove: (...args: unknown[]) => remove(...args),
    },
  };
});

import { LeadDetailView } from "./page";

describe("LeadDetailView", () => {
  beforeEach(() => {
    adminProfileState.role = "super_admin";
    adminProfileState.email = "sa@porterchain.com";
    adminProfileState.permissions = ["system:all"];
    detail.mockReset();
    conversations.mockReset();
    identities.mockReset();
    assist.mockReset();
    update.mockReset();
    convert.mockReset();
    remove.mockReset();
    routerPush.mockReset();
    vi.spyOn(window, "confirm").mockReturnValue(true);

    detail.mockResolvedValue(sampleLead());
    conversations.mockResolvedValue([]);
    identities.mockResolvedValue([
      { id: "i1", kind: "email", value_normalized: "ada@acme.test", raw_value: "ada@acme.test" },
    ]);
    assist.mockResolvedValue({
      summary: "High-intent GTA capacity ask",
      draft_reply: "Happy to quote vans for the GTA.",
      suggested_decision_status: "ready_to_convert",
      next_questions: ["Weekly volume?"],
      risks: ["Price sensitive"],
      source: "heuristic",
      proposals: [{ id: "p1", type: "reply", title: "Draft", body: "Happy to quote" }],
    });
    update.mockResolvedValue(sampleLead({ status: "contacted" }));
    convert.mockResolvedValue({ company_id: "co-1", outcome: "merchant" });
  });

  it("renders company, convert actions, assist, and delete for super_admin", async () => {
    renderWithProviders(<LeadDetailView id="lead-1" />);

    expect(await screen.findByRole("heading", { name: /acme logistics/i })).toBeInTheDocument();
    expect(screen.getAllByText("ada@acme.test").length).toBeGreaterThan(0);
    expect(screen.getByRole("button", { name: /convert to company/i })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /convert → merchant/i })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /→ customer/i })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /→ driver partner/i })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /^delete$/i })).toBeInTheDocument();
    expect(await screen.findByText(/high-intent gta capacity ask/i)).toBeInTheDocument();
    expect(screen.getByTestId("activity-timeline")).toBeInTheDocument();
  });

  it("shows not found when the lead query resolves empty", async () => {
    detail.mockResolvedValue(undefined);
    renderWithProviders(<LeadDetailView id="missing" />);
    expect(await screen.findByText(/lead not found/i)).toBeInTheDocument();
  });

  it("convert to company calls leadsApi.convert after confirm", async () => {
    const user = userEvent.setup();
    renderWithProviders(<LeadDetailView id="lead-1" />);
    await screen.findByRole("heading", { name: /acme logistics/i });
    await user.click(screen.getByRole("button", { name: /convert to company/i }));
    await waitFor(() => expect(convert).toHaveBeenCalled());
    expect(convert).toHaveBeenCalledWith(
      "test-token",
      "lead-1",
      expect.objectContaining({
        outcome: "merchant",
        create_deal: true,
        to_merchant: false,
      })
    );
  });

  it("skips convert when confirm is cancelled", async () => {
    vi.spyOn(window, "confirm").mockReturnValue(false);
    const user = userEvent.setup();
    renderWithProviders(<LeadDetailView id="lead-1" />);
    await screen.findByRole("heading", { name: /acme logistics/i });
    await user.click(screen.getByRole("button", { name: /convert to company/i }));
    expect(convert).not.toHaveBeenCalled();
  });

  it("hides Delete for sales without system:all", async () => {
    adminProfileState.role = "sales";
    adminProfileState.permissions = ["crm"];
    renderWithProviders(<LeadDetailView id="lead-1" />);
    await screen.findByRole("heading", { name: /acme logistics/i });
    expect(screen.queryByRole("button", { name: /^delete$/i })).not.toBeInTheDocument();
  });

  it("delete confirms then removes and navigates to inbox", async () => {
    const user = userEvent.setup();
    remove.mockResolvedValue(undefined);
    renderWithProviders(<LeadDetailView id="lead-1" />);
    await screen.findByRole("heading", { name: /acme logistics/i });
    await user.click(screen.getByRole("button", { name: /^delete$/i }));
    await waitFor(() => expect(remove).toHaveBeenCalledWith("test-token", "lead-1"));
    expect(routerPush).toHaveBeenCalledWith("/leads");
  });
});
