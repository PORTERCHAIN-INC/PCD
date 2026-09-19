import type { LucideIcon } from "lucide-react";
import {
  BarChart3,
  Bell,
  CreditCard,
  Key,
  LayoutDashboard,
  LifeBuoy,
  MapPinned,
  Package,
  PackagePlus,
  Settings,
  Share2,
  Truck,
  Users,
} from "lucide-react";

export type MerchantNavItem = {
  href: string;
  label: string;
  description?: string;
  icon: LucideIcon;
};

export type MerchantNavGroup = {
  id: string;
  label: string;
  items: MerchantNavItem[];
};

export const MERCHANT_NAV_GROUPS: MerchantNavGroup[] = [
  {
    id: "home",
    label: "Home",
    items: [
      {
        href: "/dashboard",
        label: "Overview",
        description: "KPIs, activity, and quick actions",
        icon: LayoutDashboard,
      },
    ],
  },
  {
    id: "operations",
    label: "Operations",
    items: [
      {
        href: "/book",
        label: "Request capacity",
        description: "Quote and book a vehicle and driver",
        icon: PackagePlus,
      },
      {
        href: "/routes",
        label: "Route Planner",
        description: "Multi-stop routes, CSV, recurring",
        icon: MapPinned,
      },
      {
        href: "/orders",
        label: "Orders",
        description: "Search, filter, and Order 360",
        icon: Package,
      },
      { href: "/track", label: "Track", description: "Live tracking and timeline", icon: Truck },
      { href: "/help", label: "Help", description: "Tickets and claims", icon: LifeBuoy },
    ],
  },
  {
    id: "finance",
    label: "Finance",
    items: [
      {
        href: "/billing",
        label: "Billing",
        description: "Invoices, statements, credits",
        icon: CreditCard,
      },
      { href: "/reports", label: "Reports", description: "Analytics and exports", icon: BarChart3 },
    ],
  },
  {
    id: "account",
    label: "Account",
    items: [
      {
        href: "/notifications",
        label: "Inbox",
        description: "Alerts and delivery updates",
        icon: Bell,
      },
      {
        href: "/api",
        label: "Integrations",
        description: "Shopify, API keys, webhooks",
        icon: Key,
      },
      {
        href: "/shopify",
        label: "Shopify",
        description: "Connect store, pickup, order sync",
        icon: Package,
      },
      {
        href: "/team",
        label: "Team",
        description: "Seats, roles, company contacts",
        icon: Users,
      },
      {
        href: "/referrals",
        label: "Referrals",
        description: "Share link and earn account credit",
        icon: Share2,
      },
      {
        href: "/settings",
        label: "Settings",
        description: "Company, locations, tax, branding",
        icon: Settings,
      },
    ],
  },
];

export const ALL_MERCHANT_NAV_ITEMS = MERCHANT_NAV_GROUPS.flatMap((g) => g.items);

/** Map nav href → authorize module key (M-25). */
export const NAV_MODULE_BY_HREF: Record<string, string> = {
  "/dashboard": "dashboard",
  "/book": "book",
  "/routes": "routes",
  "/orders": "orders",
  "/track": "tracking",
  "/help": "support",
  "/billing": "billing",
  "/reports": "reports",
  "/notifications": "support",
  "/api": "api_keys",
  "/shopify": "api_keys",
  "/team": "users",
  "/referrals": "settings",
  "/settings": "settings",
};

const EXTRA_ROUTE_MODULES: Record<string, string> = {
  "/book": "book",
  "/bulk": "bulk",
};

export function hasMerchantModule(modules: string[] | undefined, key: string): boolean {
  return Boolean(modules?.includes(key));
}

export function requiredNavModule(pathname: string): string | null {
  const extra = Object.entries(EXTRA_ROUTE_MODULES).find(
    ([href]) => pathname === href || pathname.startsWith(`${href}/`)
  );
  if (extra) return extra[1];
  const match = ALL_MERCHANT_NAV_ITEMS.filter((item) => isNavActive(pathname, item.href)).sort(
    (a, b) => b.href.length - a.href.length
  )[0];
  if (!match) return null;
  return NAV_MODULE_BY_HREF[match.href] ?? null;
}

export function filterNavGroupsByModules(modules: string[] | null | undefined): MerchantNavGroup[] {
  if (!modules || modules.length === 0) return [];
  const allowed = new Set(modules);
  return MERCHANT_NAV_GROUPS.map((group) => ({
    ...group,
    items: group.items.filter((item) => {
      const mod = NAV_MODULE_BY_HREF[item.href];
      return !mod || allowed.has(mod);
    }),
  })).filter((g) => g.items.length > 0);
}

export function isNavActive(pathname: string, href: string): boolean {
  return pathname === href || pathname.startsWith(`${href}/`);
}

export function activeNavLabel(pathname: string): string | null {
  const item = ALL_MERCHANT_NAV_ITEMS.find((i) => isNavActive(pathname, i.href));
  return item?.label ?? null;
}

export type MerchantPortalJob = "owner" | "dispatcher" | "accounting" | "viewer";

/** Same APIs, different jobs — AX. Derived from modules so the UI cannot drift from RBAC. */
export function merchantPortalJob(modules: string[] | undefined): MerchantPortalJob {
  const book = hasMerchantModule(modules, "book");
  const billing = hasMerchantModule(modules, "billing");
  const manage = hasMerchantModule(modules, "users") || hasMerchantModule(modules, "api_keys");
  if (manage || (book && billing)) return "owner";
  if (book) return "dispatcher";
  if (billing) return "accounting";
  return "viewer";
}
