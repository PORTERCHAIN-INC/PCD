import type { LucideIcon } from "lucide-react";
import {
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
  Settings,
  Shield,
  Truck,
  UserPlus,
  Users,
  Zap,
  Bot,
} from "lucide-react";

export type AdminNavItem = {
  href: string;
  label: string;
  description?: string;
  icon: LucideIcon;
};

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
    label: "Operations",
    items: [
      {
        href: "/operations",
        label: "Control Tower",
        description: "Dispatch board, SLA monitor, exceptions",
        icon: Zap,
      },
      {
        href: "/orders",
        label: "Orders",
        description: "Active deliveries and history",
        icon: Package,
      },
      {
        href: "/booking-drafts",
        label: "Booking Drafts",
        description: "Retail checkout drafts (ops recovery)",
        icon: ClipboardList,
      },
    ],
  },
  {
    id: "partners",
    label: "Partners",
    items: [
      {
        href: "/merchants",
        label: "Merchants",
        description: "Business accounts and contracts",
        icon: Building2,
      },
      {
        href: "/drivers",
        label: "Drivers",
        description: "Capacity partners and compliance",
        icon: Truck,
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
    label: "Growth",
    items: [
      {
        href: "/leads",
        label: "Lead Workspace",
        description: "Merchant, retail, driver, and newsletter inbox",
        icon: UserPlus,
      },
      {
        href: "/leads/today",
        label: "Today Dial",
        description: "Ready / follow-ups / interested call packs",
        icon: Phone,
      },
      {
        href: "/leads/agent",
        label: "Lead Agent",
        description: "Zero-human welcome, enrich, WhatsApp activity",
        icon: Bot,
      },
      {
        href: "/leads/pipeline",
        label: "Pipeline",
        description: "Leads + deals by stage",
        icon: LayoutDashboard,
      },
      {
        href: "/leads/calendar",
        label: "Sales Calendar",
        description: "Calls and meetings from guides",
        icon: CalendarDays,
      },
      {
        href: "/leads/attribution",
        label: "Lead Attribution",
        description: "Leads by source, industry, FSA and UTM",
        icon: ClipboardList,
      },
      {
        href: "/blog",
        label: "Website Blog",
        description: "Marketing content (EN / FR)",
        icon: Newspaper,
      },
      {
        href: "/blog/authors",
        label: "Blog authors",
        description: "CMS author profiles for /authors",
        icon: Users,
      },
    ],
  },
  {
    id: "finance",
    label: "Finance",
    items: [
      {
        href: "/finance",
        label: "Billing & Invoicing",
        description: "Invoices, payments, collections",
        icon: Banknote,
      },
      {
        href: "/pricing",
        label: "Pricing Center",
        description: "Catalog, merchant deals, quote simulator",
        icon: Calculator,
      },
    ],
  },
  {
    id: "support",
    label: "Support",
    items: [
      {
        href: "/support",
        label: "Support Tickets",
        description: "Customer helpdesk and SLA",
        icon: Headphones,
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
        href: "/notifications",
        label: "Notifications",
        description: "Alerts, delivery queue, templates",
        icon: Bell,
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
  "/operations",
  "/orders",
  "/booking-drafts",
  "/claims",
  "/merchants",
  "/drivers",
  "/customers",
  "/leads",
  "/leads/today",
  "/leads/agent",
  "/leads/pipeline",
  "/leads/calendar",
  "/leads/attribution",
  "/blog",
  "/blog/authors",
  "/finance",
  "/pricing",
  "/support",
  "/notifications",
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

  // Dedicated calendar/pipeline items — don't also highlight Lead Workspace.
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
