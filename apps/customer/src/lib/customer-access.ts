export type CustomerAccessProfile = {
  customer_id: string;
  email: string | null;
  clerk_user_id: string;
  is_active: boolean;
};

export async function fetchCustomerAccess(token: string): Promise<CustomerAccessProfile> {
  const api = (process.env.NEXT_PUBLIC_PORTERCHAIN_API_URL ?? "http://localhost:8001").replace(/\/$/, "");
  const res = await fetch(`${api}/v1/auth/customer/access`, {
    headers: { Authorization: `Bearer ${token}` },
  });
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new Error(typeof body.detail === "string" ? body.detail : "customer_access_denied");
  }
  return res.json();
}
