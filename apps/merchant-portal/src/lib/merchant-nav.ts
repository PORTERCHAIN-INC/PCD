import type { LucideIcon } from "lucide-react";
import {
  BarChart3,
  CreditCard,
  Key,
  LayoutDashboard,
  LifeBuoy,
  MapPinned,
  Package,
  PackagePlus,
  Settings,
  Share2,
  Store,
  Truck,
  Users,
} from "lucide-react";

export type MerchantNavItem = {
  href: string;
  label: string;
  description?: string;
  icon: LucideIcon;
  badgeKey?: "invoices" | "tickets";
};

export type MerchantNavGroup = {
  id: string;
  label: string;
  items: MerchantNavItem[];
};

/**
 * Ordered by daily use: book → orders → track, then money, then setup.
 * Inbox lives on the bell (no duplicate nav item); /notifications and /bulk stay in ⌘K.
 */
export const MERCHANT_NAV_GROUPS: MerchantNavGroup[] = [
  {
    id: "home",
    label: "",
    items: [
      {
        href: "/dashboard",
        label: "Home",
        description: "Today, spend, what needs you",
        icon: LayoutDashboard,
      },
      {
        href: "/book",
        label: "Book delivery",
        description: "Quote and book a vehicle and driver",
        icon: PackagePlus,
      },
      {
        href: "/orders",
        label: "Orders",
        description: "Search, filter, and Order 360",
        icon: Package,
      },
      { href: "/track", label: "Track", description: "Live tracking and timeline", icon: Truck },
      {
        href: "/routes",
        label: "Routes",
        description: "Multi-stop routes, CSV, recurring",
        icon: MapPinned,
      },
    ],
  },
  {
    id: "finance",
    label: "Money",
    items: [
      {
        href: "/billing",
        label: "Billing",
        description: "Invoices, statements, credits",
        icon: CreditCard,
        badgeKey: "invoices",
      },
      { href: "/reports", label: "Reports", description: "Analytics and exports", icon: BarChart3 },
    ],
  },
  {
    id: "account",
    label: "Setup",
    items: [
      {
        href: "/shopify",
        label: "Shopify",
        description: "Connect store, pickup, order sync",
        icon: Store,
      },
      {
        href: "/api",
        label: "API & webhooks",
        description: "API keys, webhooks, other integrations",
        icon: Key,
      },
      {
        href: "/team",
        label: "Team",
        description: "Seats, roles, company contacts",
        icon: Users,
      },
      {
        href: "/settings",
        label: "Settings",
        description: "Company, locations, tax, branding",
        icon: Settings,
      },
      {
        href: "/referrals",
        label: "Referrals",
        description: "Share link and earn account credit",
        icon: Share2,
      },
      {
        href: "/help",
        label: "Help",
        description: "Tickets and claims",
        icon: LifeBuoy,
        badgeKey: "tickets",
      },
    ],
  },
];

/** Reachable via ⌘K (and the bell) without a sidebar slot. */
export const MERCHANT_PALETTE_EXTRA = [
  {
    href: "/notifications",
    label: "Inbox & alerts",
    group: "Account",
    keywords: "notifications bell",
  },
  { href: "/bulk", label: "Bulk upload (CSV)", group: "Orders", keywords: "import csv" },
  { href: "/settings?tab=locations", label: "Settings › Locations", group: "Settings" },
  { href: "/settings?tab=branding", label: "Settings › Branding", group: "Settings" },
  { href: "/settings?tab=tax", label: "Settings › Tax", group: "Settings" },
  { href: "/billing?tab=cod", label: "Billing › COD", group: "Money" },
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
  "/api": "api_keys",
  "/shopify": "api_keys",
  "/team": "users",
  "/referrals": "settings",
  "/settings": "settings",
};

const EXTRA_ROUTE_MODULES: Record<string, string> = {
  "/book": "book",
  "/bulk": "bulk",
  "/notifications": "support",
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
