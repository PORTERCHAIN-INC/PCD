import type { LucideIcon } from "lucide-react";
import {
  AlertTriangle,
  Banknote,
  Bell,
  Building2,
  Calculator,
  CalendarDays,
  ClipboardList,
  Headphones,
  HeartPulse,
  LayoutDashboard,
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
  Zap,
  Bot,
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
 * Admin primary nav — ordered by daily ops workflow.
 * Top-level (ops) pages must appear here; detail/redirect routes do not.
 *
 * Groups follow the operator's day: overview → run the day (operations) →
 * manage partners (merchants / drivers / retail customers) → grow the pipeline
 * (sales/recovery/content) → money → customer care (tickets + claims) → administration.
 */
export const ADMIN_NAV_GROUPS: AdminNavGroup[] = [
  {
    id: "dashboard",
    label: "Dashboard",
    items: [
      {
        href: "/dashboard",
        label: "Dashboard",
        description: "Network KPIs and alerts",
        icon: LayoutDashboard,
      },
    ],
  },
  {
    id: "operations",
    label: "Dispatch",
    items: [
      {
        href: "/dispatch/today",
        label: "Today",
        description: "Unassigned, exceptions, board",
        icon: Zap,
      },
      {
        href: "/dispatch/plan",
        label: "Plan",
        description: "Sequence the day, check fill, commit",
        icon: Route,
      },
      {
        href: "/dispatch/live",
        label: "Live",
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
        href: "/orders",
        label: "Orders",
        description: "Active deliveries and history",
        icon: Package,
      },
      {
        href: "/dispatch/fleet",
        label: "Fleet",
        description: "Drivers, vehicles, capacity",
        icon: Truck,
      },
    ],
  },
  {
    id: "partners",
    label: "Accounts",
    items: [
      {
        href: "/merchants",
        label: "Merchants",
        description: "Business accounts and contracts",
        icon: Building2,
      },
      {
        href: "/customers",
        label: "Customers",
        description: "Retail customers and booking history",
        icon: Users,
      },
    ],
  },
  {
    id: "growth",
    // "Sales": only what drives replies, quotes and bookings. Lead Agent, Calendar
    // and Attribution stay reachable from the Inbox "More" menu; Blog moved to Administration.
    label: "Sales",
    items: [
      {
        href: "/booking-drafts",
        label: "Booking drafts",
        description: "Retail checkout drafts (ops recovery)",
        icon: ClipboardList,
      },
      {
        href: "/leads",
        label: "Inbox",
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
    ],
  },
  {
    id: "finance",
    label: "Finance",
    items: [
      {
        href: "/finance/cash",
        label: "Cash",
        description: "Who owes us, e-Transfers to match, reminders",
        icon: Wallet,
        badgeKey: "cash",
      },
      {
        href: "/finance/invoices",
        label: "Invoices",
        description: "Cycle invoices, PC codes, billing runs",
        icon: FileText,
      },
      {
        href: "/finance/payments",
        label: "Payments",
        description: "Stripe, refunds, disputes, bank payouts",
        icon: CreditCard,
      },
      {
        href: "/finance/driver-pay",
        label: "Driver Pay",
        description: "Pay runs, approvals, bank file",
        icon: Banknote,
      },
      {
        href: "/pricing",
        label: "Pricing",
        description: "Catalog, merchant deals, quote simulator",
        icon: Calculator,
      },
      {
        href: "/finance/reports",
        label: "Reports",
        description: "Margin, GST/HST, QuickBooks / Xero",
        icon: BarChart3,
      },
    ],
  },
  {
    id: "support",
    label: "Support",
    items: [
      {
        href: "/support",
        label: "Tickets",
        description: "Customer helpdesk and SLA",
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
    id: "administration",
    label: "Administration",
    items: [
      {
        href: "/blog",
        label: "Blog",
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
        label: "System",
        description: "Health, diagnostics, AI usage",
        icon: HeartPulse,
      },
      {
        href: "/settings",
        label: "Settings",
        description: "Staff, roles, integrations",
        icon: Settings,
      },
    ],
  },
];

export const ALL_ADMIN_NAV_ITEMS = ADMIN_NAV_GROUPS.flatMap((g) => g.items);

/** Top-level ops pages that must stay in the nav (redirects / nested details excluded). */
export const ADMIN_TOP_LEVEL_ROUTES = [
  "/dashboard",
  "/dispatch/today",
  "/dispatch/plan",
  "/dispatch/live",
  "/dispatch/exceptions",
  "/orders",
  "/dispatch/fleet",
  "/booking-drafts",
  "/claims",
  "/merchants",
  "/customers",
  "/leads",
  "/leads/today",
  "/leads/agent",
  "/leads/pipeline",
  "/leads/calendar",
  "/leads/attribution",
  "/blog",
  "/blog/authors",
  "/finance/cash",
  "/finance/invoices",
  "/finance/payments",
  "/finance/driver-pay",
  "/pricing",
  "/finance/reports",
  "/support",
  "/notifications",
  "/notifications/delivery",
  "/system",
  "/settings",
] as const;

function splitHref(href: string): { path: string; params: URLSearchParams } {
  const q = href.indexOf("?");
  if (q === -1) return { path: href, params: new URLSearchParams() };
  return { path: href.slice(0, q), params: new URLSearchParams(href.slice(q + 1)) };
}

/** Pathname match; when href has query params, they must match `search` (e.g. "?source=…"). */
export function isNavActive(pathname: string, href: string, search = ""): boolean {
  const { path, params } = splitHref(href);
  // Driver detail pages live under Dispatch → Fleet.
  if (path === "/dispatch/fleet" && pathname.startsWith("/drivers/")) return true;
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
  dispatcher: ["dashboard", "operations", "partners", "support"],
  fleet_manager: ["dashboard", "operations", "partners", "support"],
  sales: ["dashboard", "partners", "growth", "support"],
  merchant_success: ["dashboard", "partners", "growth", "support"],
  support: ["dashboard", "operations", "partners", "support"],
  customer_support: ["dashboard", "operations", "partners", "support"],
  finance: ["dashboard", "partners", "finance"],
  developer: ["dashboard", "administration"],
};
const SUPER_ONLY = new Set(["/system"]);
const READ_ONLY_HIDDEN = new Set(["/system", "/settings", "/blog", "/blog/authors"]);

export function adminNavForRole(role: string | null | undefined): AdminNavGroup[] {
  const r = (role ?? "").toLowerCase();
  const allowed = ROLE_GROUPS[r] ?? "all";
  return ADMIN_NAV_GROUPS.filter((g) => allowed === "all" || allowed.includes(g.id))
    .map((g) => ({
      ...g,
      items: g.items.filter((i) => {
        if (SUPER_ONLY.has(i.href) && r && r !== "super_admin" && r !== "developer") return false;
        if ((r === "read_only" || r === "auditor") && READ_ONLY_HIDDEN.has(i.href)) return false;
        return true;
      }),
    }))
    .filter((g) => g.items.length > 0);
}

/** Pages reachable only via palette (no sidebar slot) so every route stays findable. */
export const ADMIN_PALETTE_EXTRA: {
  href: string;
  label: string;
  group: string;
  keywords?: string;
}[] = [
  { href: "/leads/agent", label: "Lead agent", group: "Sales", keywords: "ai auto reply" },
  { href: "/leads/calendar", label: "Sales calendar", group: "Sales", keywords: "meetings" },
  { href: "/leads/attribution", label: "Attribution", group: "Sales", keywords: "utm campaigns" },
  { href: "/system-health", label: "System health", group: "Administration" },
  { href: "/system-tests", label: "System tests", group: "Administration" },
  { href: "/inbox", label: "Inbox (messages)", group: "Support" },
  { href: "/account", label: "My account & security", group: "Account", keywords: "passkey mfa" },
];
