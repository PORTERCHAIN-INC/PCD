import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, type RenderOptions } from "@testing-library/react";
import type { ReactElement, ReactNode } from "react";
import { vi } from "vitest";

export function createTestQueryClient() {
  return new QueryClient({
    defaultOptions: {
      queries: { retry: false, gcTime: 0 },
      mutations: { retry: false },
    },
  });
}

export function renderWithProviders(ui: ReactElement, options?: Omit<RenderOptions, "wrapper">) {
  const client = createTestQueryClient();
  function Wrapper({ children }: { children: ReactNode }) {
    return <QueryClientProvider client={client}>{children}</QueryClientProvider>;
  }
  return {
    ...render(ui, { wrapper: Wrapper, ...options }),
    queryClient: client,
  };
}

export function mockAdminAuth(
  overrides: Partial<{
    isLoaded: boolean;
    isSignedIn: boolean;
    getApiToken: () => Promise<string>;
  }> = {}
) {
  return {
    isLoaded: true,
    isSignedIn: true,
    getApiToken: vi.fn(async () => "test-token"),
    ...overrides,
  };
}

export function sampleLead(overrides: Record<string, unknown> = {}) {
  return {
    id: "lead-1",
    company_name: "Acme Logistics",
    industry: "food",
    website: null,
    business_type: null,
    address: { city: "Toronto", province: "ON" },
    primary_contact_name: "Ada Merchant",
    phone: "+14165551212",
    email: "ada@acme.test",
    estimated_deliveries_per_month: 120,
    estimated_revenue_cents: 250000,
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
    tags: ["inbound"],
    internal_notes: "Need vans this week",
    lead_score: 42,
    company_id: null,
    deal_id: null,
    contact_id: null,
    referred_by_merchant_id: null,
    merge_candidate_of: null,
    sla_first_response_due_at: null,
    last_touch_at: null,
    consent: { marketing: true },
    custom_fields: { message: "Capacity for cold chain", form: "website_contact", intent: "quote" },
    created_at: "2026-09-17T12:00:00.000Z",
    updated_at: "2026-09-17T12:00:00.000Z",
    ...overrides,
  };
}
