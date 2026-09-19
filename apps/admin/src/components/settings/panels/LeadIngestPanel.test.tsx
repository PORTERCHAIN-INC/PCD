import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import type { ReactNode } from "react";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { mockAdminAuth, renderWithProviders } from "@/test/render";

const leadIngest = vi.fn();
const updateLeadIngest = vi.fn();

vi.mock("@/hooks/useAdminAuth", () => ({
  useAdminAuth: () => mockAdminAuth(),
}));

vi.mock("@/lib/settings", () => ({
  settingsApi: {
    leadIngest: (...args: unknown[]) => leadIngest(...args),
    updateLeadIngest: (...args: unknown[]) => updateLeadIngest(...args),
  },
}));

vi.mock("@/lib/settings-metadata", () => ({
  SECTION_DESCRIPTIONS: { lead_ingest: "Webhook secrets and territory routing for CRM leads." },
}));

vi.mock("../ui/SettingsPrimitives", () => ({
  SettingsPageHeader: ({ title, description }: { title: string; description?: string }) => (
    <header>
      <h1>{title}</h1>
      {description ? <p>{description}</p> : null}
    </header>
  ),
  SettingsCard: ({ title, children }: { title: string; children: ReactNode }) => (
    <section>
      <h2>{title}</h2>
      {children}
    </section>
  ),
  BindingBadge: () => <span>env</span>,
}));

import LeadIngestPanel from "./LeadIngestPanel";

const STATUS = {
  doppler: { configured: true, project: "porterchain", config: "dev" },
  secrets: {
    PUBLIC_INGEST_API_KEY: { configured: true, in_runtime: true, in_doppler: true },
    GOOGLE_LEAD_WEBHOOK_SECRET: { configured: false, in_runtime: false, in_doppler: false },
    SOCIAL_LEAD_WEBHOOK_SECRET: { configured: false, in_runtime: false, in_doppler: false },
    META_APP_SECRET: { configured: true, in_runtime: true, in_doppler: true },
    META_WEBHOOK_VERIFY_TOKEN: { configured: true, in_runtime: true, in_doppler: true },
    META_CAPI_ACCESS_TOKEN: { configured: false, in_runtime: false, in_doppler: false },
    LINKEDIN_CAPI_TOKEN: { configured: false, in_runtime: false, in_doppler: false },
  },
  visible: {
    META_PIXEL_ID: "pixel-1",
    LINKEDIN_CONVERSION_URN: "",
    LEAD_TERRITORY_MAP_JSON: "{}",
    LEAD_ROUND_ROBIN_JSON: "[]",
    LEAD_SLA_MINUTES_JSON: '{"default":60}',
    REFERRAL_CREDIT_CENTS: 25000,
  },
  note: "Secret values are never shown.",
};

describe("LeadIngestPanel", () => {
  beforeEach(() => {
    leadIngest.mockReset();
    updateLeadIngest.mockReset();
    leadIngest.mockResolvedValue(STATUS);
    updateLeadIngest.mockResolvedValue({
      ...STATUS,
      save: { written: ["META_PIXEL_ID"] },
    });
  });

  it("loads status without leaking secret values", async () => {
    renderWithProviders(<LeadIngestPanel />);
    expect(await screen.findByRole("heading", { name: /lead ingest/i })).toBeInTheDocument();
    await waitFor(() => expect(leadIngest).toHaveBeenCalled());
    expect(screen.getByText(/public ingest api key/i)).toBeInTheDocument();
    expect(screen.getByText(/meta app secret/i)).toBeInTheDocument();
    expect(screen.getByText(/secret values never displayed/i)).toBeInTheDocument();
    expect(document.body.textContent ?? "").not.toMatch(/sk_live|EAAG/);
  });

  it("saves via settingsApi.updateLeadIngest", async () => {
    const user = userEvent.setup();
    renderWithProviders(<LeadIngestPanel />);
    await screen.findByRole("heading", { name: /lead ingest/i });
    await user.click(screen.getByRole("button", { name: /save to doppler/i }));
    await waitFor(() => expect(updateLeadIngest).toHaveBeenCalled());
    expect(updateLeadIngest.mock.calls[0]?.[1]).toEqual(
      expect.objectContaining({
        visible: expect.objectContaining({
          META_PIXEL_ID: "pixel-1",
          REFERRAL_CREDIT_CENTS: 25000,
        }),
      })
    );
  });
});
