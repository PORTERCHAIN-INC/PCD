import type { LucideIcon } from "lucide-react";
import {
  Building2,
  ClipboardList,
  CreditCard,
  FlaskConical,
  HardHat,
  Headphones,
  Bell,
  HeartPulse,
  LayoutDashboard,
  Map,
  Newspaper,
  Package,
  Settings,
  Shield,
  Truck,
  UserPlus,
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

export const ADMIN_NAV_GROUPS: AdminNavGroup[] = [
  {
    id: "home",
    label: "Home",
    items: [
      {
        href: "/dashboard",
        label: "Dashboard",
        description: "KPIs, alerts, and network overview",
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
        description: "Dispatch board & SLA",
        icon: Zap,
      },
      { href: "/live-map", label: "Live Map", description: "Real-time fleet map", icon: Map },
      { href: "/orders", label: "Orders", description: "Order 360 & lifecycle", icon: Package },
      {
        href: "/booking-drafts",
        label: "Booking Drafts",
        description: "In-progress checkouts",
        icon: ClipboardList,
      },
      { href: "/claims", label: "Claims", description: "Insurance & damage claims", icon: Shield },
    ],
  },
  {
    id: "commerce",
    label: "Commerce",
    items: [
      {
        href: "/leads",
        label: "Merchant Leads",
        description: "Quotes, contact & business inquiries",
        icon: UserPlus,
      },
      {
        href: `/leads?source=${DRIVER_LEAD_SOURCE}`,
        label: "Driver Leads",
        description: "Vehicle partner applications (/vehicle-partner)",
        icon: HardHat,
      },
      {
        href: "/blog",
        label: "Blog",
        description: "Create, edit & publish website posts (EN + FR)",
        icon: Newspaper,
      },
      {
        href: "/merchants",
        label: "Merchants",
        description: "B2B accounts & contracts",
        icon: Building2,
      },
      {
        href: "/drivers",
        label: "Drivers",
        description: "Active fleet partners & compliance",
        icon: Truck,
      },
    ],
  },
  {
    id: "finance",
    label: "Finance",
    items: [
      { href: "/pricing", label: "Pricing", description: "Tariffs & simulator", icon: CreditCard },
      { href: "/finance", label: "Finance", description: "Invoices & payments", icon: CreditCard },
    ],
  },
  {
    id: "support",
    label: "Support",
    items: [
      { href: "/support", label: "Support Center", description: "Tickets & SLA", icon: Headphones },
      {
        href: "/notifications",
        label: "Notifications",
        description: "Queue, delivery & devices",
        icon: Bell,
      },
      {
        href: "/system-health",
        label: "System Health",
        description: "Platform health dashboard",
        icon: HeartPulse,
      },
      {
        href: "/system-tests",
        label: "System Tests",
        description: "Validation & diagnostics",
        icon: FlaskConical,
      },
      { href: "/settings", label: "Settings", description: "Integrations & RBAC", icon: Settings },
    ],
  },
];

export const ALL_ADMIN_NAV_ITEMS = ADMIN_NAV_GROUPS.flatMap((g) => g.items);

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

  return true;
}

export function activeNavLabel(pathname: string, search = ""): string | null {
  // Prefer more specific query-bearing items first.
  const ranked = [...ALL_ADMIN_NAV_ITEMS].sort((a, b) => {
    const aq = a.href.includes("?") ? 1 : 0;
    const bq = b.href.includes("?") ? 1 : 0;
    return bq - aq;
  });
  const item = ranked.find((i) => isNavActive(pathname, i.href, search));
  return item?.label ?? null;
}
