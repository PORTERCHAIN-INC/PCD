import { publicEnv } from "@/lib/env";

const API_BASE = publicEnv.porterchainApiUrl;

export type ReferralCredit = {
  id: string;
  merchant_id: string;
  lead_id: string;
  company_id: string | null;
  amount_cents: number;
  currency: string;
  status: string;
  notes: string | null;
  created_at: string | null;
  granted_at: string | null;
};

export type ReferredLead = {
  id: string;
  company_name: string;
  primary_contact_name: string | null;
  email: string | null;
  status: string;
  decision_status: string | null;
  channel: string | null;
  lead_score: number;
  created_at: string | null;
};

export type ReferralOverview = {
  merchant_id: string;
  share_url: string;
  credit_cents: number;
  currency: string;
  credits: ReferralCredit[];
  referred_leads: ReferredLead[];
};

export type ReferralSubmitInput = {
  company_name: string;
  email?: string;
  phone?: string;
  contact_name?: string;
  notes?: string;
};

async function referralFetch<T>(
  path: string,
  token: string,
  init?: RequestInit & { orgId?: string }
): Promise<T> {
  const { orgId, ...rest } = init ?? {};
  const headers: Record<string, string> = {
    Authorization: `Bearer ${token}`,
  };
  if (orgId) headers["X-Merchant-Id"] = orgId;
  if (rest.body && !(rest.body instanceof FormData)) {
    headers["Content-Type"] = "application/json";
  }
  const response = await fetch(`${API_BASE}${path}`, {
    ...rest,
    headers: { ...headers, ...(rest.headers as Record<string, string> | undefined) },
  });
  if (!response.ok) {
    const body = await response.json().catch(() => ({}));
    throw new Error(typeof body.detail === "string" ? body.detail : `API error ${response.status}`);
  }
  if (response.status === 204) return undefined as T;
  return response.json() as Promise<T>;
}

export const referralsApi = {
  overview: (token: string, orgId?: string) =>
    referralFetch<ReferralOverview>("/v1/merchant/referrals", token, { orgId }),

  submit: (token: string, body: ReferralSubmitInput, orgId?: string) =>
    referralFetch<{ id: string }>("/v1/merchant/referrals", token, {
      method: "POST",
      body: JSON.stringify(body),
      orgId,
    }),
};
