export type MerchantAccessProfile = {
  company_name: string;
  email: string;
  status: string;
  merchant_id?: string;
  enterprise_role?: string;
  logo_url?: string | null;
};

/** Build merchant shell profile from SpiceDB session-context (no /access). */
export function merchantProfileFromSession(ctx: {
  email: string | null;
  status: string;
  organization_ids?: string[];
  roles: string[];
}): MerchantAccessProfile {
  return {
    company_name: "Merchant",
    email: ctx.email ?? "",
    status: ctx.status === "active" ? "active" : ctx.status,
    merchant_id: ctx.organization_ids?.[0],
    enterprise_role: ctx.roles[0],
  };
}
