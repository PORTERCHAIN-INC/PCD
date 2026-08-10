import { adminFetch } from "@/lib/api";

export type CustomerRow = {
  id: string;
  email: string;
  phone: string | null;
  customer_reference: string | null;
  display_name: string;
  clerk_user_id: string | null;
  clerk_linked: boolean;
  identity_status: string;
  stripe_customer_id?: string | null;
  privacy_status: string | null;
  privacy_hold_reference: string | null;
  lifetime_orders: number;
  lifetime_revenue_cents: number;
  open_support_tickets: number;
  created_at: string | null;
};

export type CustomerDetail = CustomerRow & {
  recent_orders: Array<{
    order_id: string;
    order_number: string;
    tracking_number: string;
    state: string;
    amount_cents: number;
  }>;
};

export type CustomerOrder = {
  id: string;
  order_number: string;
  tracking_number: string;
  state: string;
  amount_cents: number;
  currency: string;
  scheduled_at: string | null;
  created_at: string | null;
};

const B = "/v1/admin/customers";

const qs = (params: Record<string, string | undefined>) => {
  const s = new URLSearchParams();
  for (const [k, v] of Object.entries(params)) if (v) s.set(k, v);
  const out = s.toString();
  return out ? `?${out}` : "";
};

export const customersApi = {
  list: (t: string, params: Record<string, string | undefined> = {}) =>
    adminFetch<CustomerRow[]>(`${B}${qs(params)}`, t),
  detail: (t: string, id: string) => adminFetch<CustomerDetail>(`${B}/${id}`, t),
  orders: (t: string, id: string, limit = 50) =>
    adminFetch<CustomerOrder[]>(`${B}/${id}/orders?limit=${limit}`, t),
};
