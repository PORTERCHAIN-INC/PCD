import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { adminProfileState } from "@/test/admin-profile-state";
import { mockAdminAuth, renderWithProviders, sampleLead } from "@/test/render";

const detail = vi.fn();
const get360 = vi.fn();
const resolveMerge = vi.fn();
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
      get360: (...args: unknown[]) => get360(...args),
      resolveMerge: (...args: unknown[]) => resolveMerge(...args),
      conversations: (...args: unknown[]) => conversations(...args),
      identities: (...args: unknown[]) => identities(...args),
      assist: (...args: unknown[]) => assist(...args),
      update: (...args: unknown[]) => update(...args),
      convert: (...args: unknown[]) => convert(...args),
      remove: (...args: unknown[]) => remove(...args),
      quote: (...args: unknown[]) => quoteApi(...args),
      fitScore: (...args: unknown[]) => fitScore(...args),
      draft: (...args: unknown[]) => draftApi(...args),
      markLost: (...args: unknown[]) => markLost(...args),
      replyChannels: () =>
        Promise.resolve({
          email: { enabled: true, transport: "zoho_smtp", from: "sales@porterchain.com" },
          whatsapp: { enabled: false, reason: "whatsapp_cloud_disabled" },
          call_outcomes: ["connected"],
        }),
      reply: (...args: unknown[]) => reply(...args),
    },
  };
});

const quoteApi = vi.fn();
const fitScore = vi.fn();
const draftApi = vi.fn();
const markLost = vi.fn();
const reply = vi.fn();

import { LeadDetailView } from "@/components/leads/LeadDetailClient";

describe("LeadDetailView", () => {
  beforeEach(() => {
    adminProfileState.role = "super_admin";
    adminProfileState.email = "sa@porterchain.com";
    adminProfileState.permissions = ["system:all"];
    detail.mockReset();
    get360.mockReset();
    resolveMerge.mockReset();
    conversations.mockReset();
    identities.mockReset();
    assist.mockReset();
    update.mockReset();
    convert.mockReset();
    remove.mockReset();
    routerPush.mockReset();
    vi.spyOn(window, "confirm").mockReturnValue(true);

    detail.mockResolvedValue(sampleLead());
    get360.mockResolvedValue({
      lead: sampleLead(),
      retail_lead: null,
      identities: [],
      conversations: [],
      tasks: [],
      nurture: {},
      activities: [],
      visitor: { session_id: "vid-1", intent_score: 12 },
      quotes: [],
      drafts: [],
      abandoned_checkouts: [],
      referral: null,
      sla: { breached: false },
      assignee: { id: "admin-1", name: "Ops", email: "ops@porterchain.com" },
      consent: {},
      score: { lead_score: 40 },
      merge_candidate_of: null,
      urgent_unassigned_tasks: [],
    });
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
    update.mockResolvedValue(sampleLead({ status: "replied" }));
    convert.mockResolvedValue({ company_id: "co-1", outcome: "merchant" });
    quoteApi.mockResolvedValue({
      available: true,
      amount_cents: 10170,
      amount_display: "$101.70",
      pricing: "retail",
      vehicle_class: "cargo_van",
      vehicle_label: "cargo van",
      pickup_fsa: "M5V",
      dropoff_fsa: "M4C",
      parcel_count: 1,
      distance_km: 9.5,
      lines: [],
      tax_cents: 1170,
      booking_url: "https://porterchain.com/en/book?pc_lead=lead-1",
      note: "",
    });
    fitScore.mockResolvedValue({
      score: 84,
      version: "fit-v1",
      reasons: [{ label: "Target industry: Pharmacy", points: 30 }],
    });
    draftApi.mockResolvedValue({
      channel: "email",
      subject: "Your PorterChain delivery quote: $101.70",
      body: "Hi Ada, ... $101.70 ... https://porterchain.com/en/book?pc_lead=lead-1",
      template: "Pharmacy",
      with_quote: true,
      source: "template",
    });
    markLost.mockResolvedValue({ status: "lost" });
    reply.mockReset();
    reply.mockResolvedValue({ id: "m1", channel: "email", status: "sent", to: "ada@acme.test" });
  });

  it("instant quote + score; Send quote only fills the composer, admin presses Send", async () => {
    const user = userEvent.setup();
    renderWithProviders(<LeadDetailView id="lead-1" />);
    expect(await screen.findByText("$101.70")).toBeInTheDocument();
    expect(await screen.findByText("Target industry: Pharmacy")).toBeInTheDocument();
    await user.click(screen.getAllByRole("button", { name: /send quote/i })[0]);
    await waitFor(() => expect(draftApi).toHaveBeenCalled());
    const box = await screen.findByRole("textbox", { name: /reply message/i });
    await waitFor(() => expect((box as HTMLTextAreaElement).value).toContain("pc_lead=lead-1"));
    expect(reply).not.toHaveBeenCalled(); // nothing sent yet
    expect(screen.getByText(/quote attached/i)).toBeInTheDocument();
    const sendButtons = screen.getAllByRole("button", { name: /^send quote$/i });
    await user.click(sendButtons[sendButtons.length - 1]);
    await waitFor(() => expect(reply).toHaveBeenCalledTimes(1));
    expect(reply.mock.calls[0][2]).toMatchObject({ channel: "email", attach_quote: true });
  });

  it("marks a lead lost in one tap", async () => {
    const user = userEvent.setup();
    renderWithProviders(<LeadDetailView id="lead-1" />);
    await user.click(await screen.findByRole("button", { name: "Price" }));
    await waitFor(() => expect(markLost).toHaveBeenCalledWith(expect.anything(), "lead-1", "price"));
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
