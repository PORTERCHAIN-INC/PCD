import { publicEnv } from "@/lib/env";

const API_BASE = publicEnv.porterchainApiUrl;

export type MerchantContact = {
  id: string;
  company_id: string | null;
  first_name: string;
  last_name: string | null;
  designation: string | null;
  department: string | null;
  phone: string | null;
  mobile: string | null;
  email: string | null;
  linkedin: string | null;
  birthday: string | null;
  roles: string[];
  is_primary: boolean;
  created_at: string | null;
  source: "manual" | "team";
  team_user_id: string | null;
  team_role: string | null;
  can_delete: boolean;
};

export type ContactInput = {
  first_name: string;
  last_name?: string;
  designation?: string;
  department?: string;
  phone?: string;
  mobile?: string;
  email?: string;
  linkedin?: string;
  is_primary?: boolean;
  roles?: string[];
};

async function contactsFetch<T>(
  path: string,
  token: string,
  init?: RequestInit & { orgId?: string }
): Promise<T> {
  const headers: Record<string, string> = {
    Authorization: `Bearer ${token}`,
    "X-Porterchain-Portal": "merchant",
  };
  if (init?.body && !(init.body instanceof FormData)) {
    headers["Content-Type"] = "application/json";
  }
  const response = await fetch(`${API_BASE}${path}`, {
    ...init,
    headers: { ...headers, ...(init?.headers as Record<string, string>) },
  });
  if (!response.ok) {
    const body = await response.json().catch(() => ({}));
    throw new Error(body.detail || `API error ${response.status}`);
  }
  if (response.status === 204) return undefined as T;
  return response.json() as Promise<T>;
}

export const contactsApi = {
  list: (token: string, orgId?: string) =>
    contactsFetch<MerchantContact[]>("/v1/merchant/contacts", token, { orgId }),

  create: (token: string, body: ContactInput, orgId?: string) =>
    contactsFetch<MerchantContact>("/v1/merchant/contacts", token, {
      method: "POST",
      body: JSON.stringify(body),
      orgId,
    }),

  update: (token: string, contactId: string, body: Partial<ContactInput>, orgId?: string) =>
    contactsFetch<MerchantContact>(`/v1/merchant/contacts/${contactId}`, token, {
      method: "PATCH",
      body: JSON.stringify(body),
      orgId,
    }),

  remove: (token: string, contactId: string, orgId?: string) =>
    contactsFetch<void>(`/v1/merchant/contacts/${contactId}`, token, {
      method: "DELETE",
      orgId,
    }),
};
