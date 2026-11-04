import type { LucideIcon } from "lucide-react";
import {
  AlertTriangle,
  Banknote,
  Bell,
  Building2,
  Calculator,
  ClipboardList,
  Headphones,
  HeartPulse,
  Newspaper,
  Package,
  Phone,
  Radio,
  Route,
  Settings,
  Shield,
  Truck,
  UserPlus,
  Users,
  BarChart3,
  CreditCard,
  FileText,
  Wallet,
  KanbanSquare,
  MailCheck,
  PenLine,
} from "lucide-react";

export type AdminNavItem = {
  href: string;
  label: string;
  description?: string;
  icon: LucideIcon;
  /** Live "needs action" count shown as a badge (see useAdminNavBadges). */
  badgeKey?: AdminBadgeKey;
};

export type AdminBadgeKey = "exceptions" | "leads" | "calls" | "cash" | "tickets";

export type AdminNavGroup = {
  id: string;
  label: string;
  items: AdminNavItem[];
};

export const DRIVER_LEAD_SOURCE = "website_driver_partner";
export const WEBSITE_CONTACT_LEAD_SOURCE = "website_contact";
export const WEBSITE_NEWSLETTER_LEAD_SOURCE = "website_newsletter";

/**
 * Admin primary nav (doc 75 §2, D-75-1): Today · Orders · Dispatch · Network ·
 * Customers & Orgs · Billing · Support · Insights · Settings.
 * Top-level (ops) pages must appear here; detail/redirect routes do not.
 */
export const ADMIN_NAV_GROUPS: AdminNavGroup[] = [
  {
    id: "today",
    label: "Today",
    items: [
      {
        href: "/today",
        label: "Today",
        description: "Pickups, live, exceptions, tickets due, network KPIs",
        icon: Radio,
        badgeKey: "exceptions",
      },
    ],
  },
  {
    id: "orders",
    label: "Orders",
    items: [
      {
        href: "/orders",
        label: "All orders",
        description: "Active deliveries and history",
        icon: Package,
      },
      {
        href: "/booking-drafts",
        label: "Booking drafts",
        description: "Retail checkout drafts (ops recovery)",
        icon: ClipboardList,
      },
    ],
  },
  {
    id: "dispatch",
    label: "Dispatch",
    items: [
      {
        href: "/dispatch/plan",
        label: "Plan",
        description: "Sequence the day, check fill, commit",
        icon: Route,
      },
      {
        href: "/dispatch/live",
        label: "Live map",
        description: "Map and ETAs vs promise",
        icon: Radio,
      },
      {
        href: "/dispatch/exceptions",
        label: "Exceptions",
        description: "One queue, worst first",
        icon: AlertTriangle,
        badgeKey: "exceptions",
      },
      {
        href: "/dispatch/fleet",
        label: "Fleet & vehicles",
        description: "Vehicles and capacity",
        icon: Truck,
      },
      {
        href: "/dispatch/batches",
        label: "Bulk batches",
        description: "Merchant CSV batches, routes and handovers",
        icon: Package,
      },
    ],
  },
  {
    id: "network",
    label: "Network",
    items: [
      {
        href: "/drivers",
        label: "Drivers",
        description: "Driver profiles, documents, pay",
        icon: Users,
      },
      {
        href: "/partners",
        label: "Partners",
        description: "Couriers, linehaul, 3PL, warehouses, customs agents",
        icon: Truck,
      },
      {
        href: "/partners/jobs",
        label: "Partner jobs",
        description: "Legs handed to partners and their status",
        icon: Route,
      },
      {
        href: "/partners/contracts",
        label: "Fleet contracts",
        description: "Contractor fleet rates and payable statements",
        icon: FileText,
      },
    ],
  },
  {
    id: "customers",
    label: "Customers & Orgs",
    items: [
      {
        href: "/merchants",
        label: "Organisations",
        description: "Business accounts by type, contracts, pricing",
        icon: Building2,
      },
      {
        href: "/orgs",
        label: "Types & packs",
        description: "Business type review, capabilities, operating profile",
        icon: Building2,
      },
      {
        href: "/customers",
        label: "People",
        description: "Retail customers and booking history",
        icon: Users,
      },
      {
        href: "/leads",
        label: "Leads",
        description: "Every lead, answered in under 5 minutes",
        icon: UserPlus,
        badgeKey: "leads",
      },
      {
        href: "/leads/pipeline",
        label: "Pipeline",
        description: "New → Replied → Quoted → Won / Lost",
        icon: KanbanSquare,
      },
      {
        href: "/leads/today",
        label: "Call list",
        description: "Who to phone today",
        icon: Phone,
        badgeKey: "calls",
      },
      {
        href: "/merchants/duplicates",
        label: "Duplicates",
        description: "Find and merge duplicate accounts",
        icon: Building2,
      },
    ],
  },
  {
    id: "billing",
    label: "Billing",
    items: [
      {
        href: "/finance/invoices",
        label: "Invoices",
        description: "Cycle invoices, PC codes, billing runs",
        icon: FileText,
      },
      {
        href: "/finance/payments",
        label: "Payments",
        description: "Interac matching, refunds, disputes, payouts",
        icon: CreditCard,
      },
      {
        href: "/finance/driver-pay",
        label: "Driver & partner pay",
        description: "Pay runs, approvals, bank file",
        icon: Banknote,
      },
      {
        href: "/pricing",
        label: "Rate cards & pricing",
        description: "Standard rate card, org pricing, quote simulator",
        icon: Calculator,
      },
      {
        href: "/finance/tax-registration",
        label: "Tax (GST/HST)",
        description: "Registration and filings",
        icon: FileText,
      },
      {
        href: "/finance/cash",
        label: "Cash",
        description: "Who owes us, e-Transfers to match, reminders",
        icon: Wallet,
        badgeKey: "cash",
      },
    ],
  },
  {
    id: "support",
    label: "Support",
    items: [
      {
        href: "/support",
        label: "Unified inbox",
        description: "Tickets, email and lead replies, SLA",
        icon: Headphones,
        badgeKey: "tickets",
      },
      {
        href: "/claims",
        label: "Claims",
        description: "Damage, loss and insurance cases",
        icon: Shield,
      },
    ],
  },
  {
    id: "insights",
    label: "Insights",
    items: [
      {
        href: "/finance/reports",
        label: "Reports",
        description: "Margin, GST/HST, QuickBooks / Xero",
        icon: BarChart3,
      },
      {
        href: "/finance/metrics",
        label: "Unit economics",
        description: "EVA, break-even, payback, queueing",
        icon: BarChart3,
      },
      {
        href: "/finance/analytics",
        label: "Analytics",
        description: "Trends and unit economics",
        icon: BarChart3,
      },
      {
        href: "/leads/attribution",
        label: "Attribution",
        description: "UTM and campaign sources",
        icon: BarChart3,
      },
    ],
  },
  {
    id: "settings",
    label: "Settings",
    items: [
      {
        href: "/settings",
        label: "Team & roles",
        description: "Staff, roles, integrations",
        icon: Settings,
      },
      {
        href: "/notifications",
        label: "Notifications",
        description: "Your alerts inbox",
        icon: Bell,
      },
      {
        href: "/notifications/delivery",
        label: "Delivery center",
        description: "Email log, speed, bounces, templates",
        icon: MailCheck,
      },
      {
        href: "/system",
        label: "System health & tests",
        description: "Health, diagnostics, tests",
        icon: HeartPulse,
      },
      {
        href: "/blog",
        label: "Website & blog",
        description: "Marketing content (EN / FR)",
        icon: Newspaper,
      },
      {
        href: "/blog/authors",
        label: "Blog authors",
        description: "CMS author profiles for /authors",
        icon: PenLine,
      },
      {
        href: "/account/security",
        label: "My security",
        description: "Passkeys and MFA",
        icon: Shield,
      },
    ],
  },
];

export const ALL_ADMIN_NAV_ITEMS = ADMIN_NAV_GROUPS.flatMap((g) => g.items);

/** Top-level ops pages that must stay in the nav (redirects / nested details excluded). */
export const ADMIN_TOP_LEVEL_ROUTES = [
  "/today",
  "/orders",
  "/booking-drafts",
  "/dispatch/plan",
  "/dispatch/live",
  "/dispatch/exceptions",
  "/dispatch/fleet",
  "/dispatch/batches",
  "/drivers",
  "/partners",
  "/partners/jobs",
  "/partners/contracts",
  "/merchants",
  "/orgs",
  "/customers",
  "/leads",
  "/leads/pipeline",
  "/leads/today",
  "/merchants/duplicates",
  "/finance/invoices",
  "/finance/payments",
  "/finance/metrics",
  "/finance/driver-pay",
  "/pricing",
  "/finance/tax-registration",
  "/finance/cash",
  "/support",
  "/claims",
  "/finance/reports",
  "/finance/analytics",
  "/leads/attribution",
  "/settings",
  "/notifications",
  "/notifications/delivery",
  "/system",
  "/blog",
  "/blog/authors",
  "/account/security",
  "/dispatch/today",
  "/leads/agent",
  "/leads/calendar",
  "/inbox",
] as const;

function splitHref(href: string): { path: string; params: URLSearchParams } {
  const q = href.indexOf("?");
  if (q === -1) return { path: href, params: new URLSearchParams() };
  return { path: href.slice(0, q), params: new URLSearchParams(href.slice(q + 1)) };
}

/** Pathname match; when href has query params, they must match `search` (e.g. "?source=…"). */
export function isNavActive(pathname: string, href: string, search = ""): boolean {
  const { path, params } = splitHref(href);
  const pathMatch = pathname === path || pathname.startsWith(`${path}/`);
  if (!pathMatch) return false;

  const current = new URLSearchParams(search.startsWith("?") ? search.slice(1) : search);

  if ([...params.keys()].length > 0) {
    for (const [key, value] of params.entries()) {
      if (current.get(key) !== value) return false;
    }
    return true;
  }

  // Bare /leads = all-inbox workspace (not a source= filter deep-link).
  if (
    path === "/leads" &&
    [DRIVER_LEAD_SOURCE, WEBSITE_CONTACT_LEAD_SOURCE, WEBSITE_NEWSLETTER_LEAD_SOURCE].includes(
      current.get("source") ?? ""
    )
  ) {
    return false;
  }

  // Dedicated calendar/pipeline items — don't also highlight Inbox.
  if (
    path === "/leads" &&
    (pathname.startsWith("/leads/calendar") ||
      pathname.startsWith("/leads/pipeline") ||
      pathname.startsWith("/leads/today") ||
      pathname.startsWith("/leads/agent"))
  ) {
    return false;
  }

  return true;
}

export function activeNavLabel(pathname: string, search = ""): string | null {
  const ranked = [...ALL_ADMIN_NAV_ITEMS].sort((a, b) => {
    const aq = a.href.includes("?") ? 1 : 0;
    const bq = b.href.includes("?") ? 1 : 0;
    return bq - aq;
  });
  const item = ranked.find((i) => isNavActive(pathname, i.href, search));
  return item?.label ?? null;
}

/**
 * Role-aware nav: hide what a role can't use (the API still enforces access).
 * super_admin sees everything; admin sees everything except System diagnostics.
 */
const ROLE_GROUPS: Record<string, string[] | "all"> = {
  super_admin: "all",
  admin: "all",
  operations_manager: "all",
  read_only: "all",
  auditor: "all",
  dispatcher: ["today", "orders", "dispatch", "network", "customers", "support"],
  fleet_manager: ["today", "orders", "dispatch", "network", "support"],
  sales: ["today", "customers", "support", "insights"],
  merchant_success: ["today", "customers", "support"],
  support: ["today", "orders", "customers", "support"],
  customer_support: ["today", "orders", "customers", "support"],
  finance: ["today", "customers", "billing", "insights"],
  developer: ["today", "settings"],
};
const SUPER_ONLY = new Set(["/system"]);
const READ_ONLY_HIDDEN = new Set(["/system", "/settings", "/blog", "/blog/authors"]);
/** Everyone keeps their own security page, whatever the role. */
const ALWAYS = new Set(["/account/security"]);

export function adminNavForRole(role: string | null | undefined): AdminNavGroup[] {
  const r = (role ?? "").toLowerCase();
  const allowed = ROLE_GROUPS[r] ?? "all";
  return ADMIN_NAV_GROUPS.map((g) => ({
    ...g,
    items: g.items.filter((i) => {
      if (allowed !== "all" && !allowed.includes(g.id)) return ALWAYS.has(i.href);
      if (SUPER_ONLY.has(i.href) && r && r !== "super_admin" && r !== "developer") return false;
      if ((r === "read_only" || r === "auditor") && READ_ONLY_HIDDEN.has(i.href)) return false;
      return true;
    }),
  })).filter((g) => g.items.length > 0);
}

/** Pages reachable only via palette (no sidebar slot) so every route stays findable. */
export const ADMIN_PALETTE_EXTRA: {
  href: string;
  label: string;
  group: string;
  keywords?: string;
}[] = [
  {
    href: "/dispatch/today",
    label: "Pickup queue",
    group: "Dispatch",
    keywords: "classic queue unassigned board",
  },
  {
    href: "/leads/agent",
    label: "Lead agent",
    group: "Customers & Orgs",
    keywords: "ai auto reply",
  },
  {
    href: "/leads/calendar",
    label: "Sales calendar",
    group: "Customers & Orgs",
    keywords: "meetings",
  },
  { href: "/inbox", label: "Inbox (messages)", group: "Support" },
];
