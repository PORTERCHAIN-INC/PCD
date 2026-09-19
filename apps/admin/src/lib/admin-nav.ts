import type { LucideIcon } from "lucide-react";
import {
  Banknote,
  Bell,
  Building2,
  Calculator,
  CalendarDays,
  ClipboardList,
  HardHat,
  Headphones,
  HeartPulse,
  LayoutDashboard,
  Newspaper,
  Package,
  Settings,
  Shield,
  Truck,
  UserPlus,
  Users,
  Zap,
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
        description: "Abandoned checkouts to recover",
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
        label: "Merchant Leads",
        description: "Inbound business inquiries",
        icon: UserPlus,
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
        href: `/leads?source=${DRIVER_LEAD_SOURCE}`,
        label: "Driver Applications",
        description: "Vehicle partner applications",
        icon: HardHat,
      },
      {
        href: "/blog",
        label: "Website Blog",
        description: "Marketing content (EN / FR)",
        icon: Newspaper,
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
        label: "System Health",
        description: "Probes, diagnostics, integrations",
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
  "/leads/pipeline",
  "/leads/calendar",
  "/blog",
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

  // Bare /leads = merchant inbox (not the driver-partner filter).
  if (path === "/leads" && current.get("source") === DRIVER_LEAD_SOURCE) {
    return false;
  }

  // Dedicated calendar item — don't also highlight Merchant Leads.
  if (path === "/leads" && pathname.startsWith("/leads/calendar")) {
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

export function navCoversAllTopLevelRoutes(): { ok: boolean; missing: string[] } {
  const navPaths = new Set(ALL_ADMIN_NAV_ITEMS.map((i) => splitHref(i.href).path));
  const missing = ADMIN_TOP_LEVEL_ROUTES.filter((r) => !navPaths.has(r));
  return { ok: missing.length === 0, missing: [...missing] };
}
