export interface SupportTicketRow {
  id: string;
  ticket_number?: string;
  subject: string;
  status: string;
  priority: string;
  category?: string;
  order_id?: string | null;
  order_number?: string | null;
  tracking_number?: string | null;
  description?: string | null;
  sla_status?: string | null;
  created_at?: string | null;
  updated_at?: string | null;
}

export interface ClaimRow {
  id: string;
  claim_number?: string;
  claim_type: string;
  status: string;
  order_id: string;
  order_number?: string | null;
  tracking_number?: string | null;
  amount_cents?: number;
  description?: string | null;
  created_at?: string | null;
  resolved_at?: string | null;
}

export interface IncidentRow {
  id: string;
  incident_type: string;
  description: string;
  order_id?: string | null;
  status: string;
  claim_id?: string;
  created_at: string;
}

export interface IncidentType {
  id: string;
  label: string;
  creates_claim: boolean;
  claim_type: string | null;
  priority: string;
}

export interface EmergencyContact {
  name?: string | null;
  phone?: string | null;
  relationship?: string | null;
  ops_hotline: string;
  ops_email: string;
}

export interface KbArticle {
  id: string;
  category_id: string;
  title: string;
  body: string;
  published?: boolean;
}

export interface DriverSupportSnapshot {
  tickets: SupportTicketRow[];
  claims: ClaimRow[];
  incidents: IncidentRow[];
  incident_types: IncidentType[];
  emergency_contact: EmergencyContact;
  knowledge_base: {
    categories: Array<{ id: string; name: string }>;
    articles: KbArticle[];
    faq: Array<{ question: string; answer: string }>;
  };
  chat: {
    enabled: boolean;
    status: string;
    message: string;
    channel_id: string | null;
  };
  last_updated: string;
}

export function incidentLabel(type: string, types: IncidentType[]): string {
  return types.find((t) => t.id === type)?.label ?? type.replace(/_/g, " ");
}

export function formatSupportDate(iso: string | null | undefined): string {
  if (!iso) return "—";
  return new Date(iso).toLocaleString(undefined, {
    month: "short",
    day: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

export function priorityStyle(priority: string): string {
  const p = priority.toLowerCase();
  if (p === "critical") return "bg-red-100 text-red-800";
  if (p === "high") return "bg-amber-100 text-amber-900";
  return "bg-gray-100 text-gray-700";
}

export function statusStyle(status: string): string {
  const s = status.toLowerCase();
  if (s === "open" || s === "new") return "bg-blue-100 text-blue-800";
  if (s === "resolved" || s === "closed" || s === "compensated") return "bg-emerald-100 text-emerald-800";
  if (s.includes("investigat") || s.includes("waiting")) return "bg-amber-100 text-amber-900";
  return "bg-gray-100 text-gray-700";
}
