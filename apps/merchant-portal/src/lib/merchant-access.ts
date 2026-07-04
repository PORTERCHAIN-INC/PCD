import { publicEnv } from "@/lib/env";

export type MerchantAccessProfile = {
  company_name: string;
  email: string;
  status: string;
  merchant_id?: string;
  enterprise_role?: string;
};

export async function fetchMerchantAccess(
  token: string
): Promise<MerchantAccessProfile> {
  const res = await fetch(`${publicEnv.porterchainApiUrl}/v1/auth/merchant/access`, {
    headers: { Authorization: `Bearer ${token}` },
    cache: "no-store",
  });

  if (!res.ok) {
    const body = await res.json().catch(() => ({ detail: res.statusText }));
    const detail = typeof body.detail === "string" ? body.detail : "merchant_access_denied";
    throw new Error(detail);
  }

  const data = (await res.json()) as {
    company_name: string;
    email: string;
    is_active: boolean;
    merchant_id: string;
    enterprise_role: string;
  };

  return {
    company_name: data.company_name,
    email: data.email,
    status: data.is_active ? "active" : "inactive",
    merchant_id: data.merchant_id,
    enterprise_role: data.enterprise_role,
  };
}
