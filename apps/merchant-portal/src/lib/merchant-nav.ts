import type { LucideIcon } from "lucide-react";
import {
  BarChart3,
  Bell,
  CreditCard,
  FileSpreadsheet,
  Key,
  LayoutDashboard,
  Package,
  Settings,
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
        label: "Book Delivery",
        description: "Single & multi-parcel booking",
        icon: Truck,
      },
      {
        href: "/bulk",
        label: "Bulk Upload",
        description: "CSV import and confirm",
        icon: FileSpreadsheet,
      },
      {
        href: "/orders",
        label: "Orders",
        description: "Search, filter, and Order 360",
        icon: Package,
      },
      { href: "/track", label: "Track", description: "Live tracking and timeline", icon: Truck },
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
        label: "Notifications",
        description: "Alerts and delivery updates",
        icon: Bell,
      },
      { href: "/api", label: "Integrations", description: "API keys, webhooks, usage", icon: Key },
      {
        href: "/team",
        label: "Team & contacts",
        description: "Contacts, seats, roles",
        icon: Users,
      },
      {
        href: "/settings",
        label: "Business Profile",
        description: "Locations, tax, support, claims",
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
  "/bulk": "bulk",
  "/orders": "orders",
  "/track": "tracking",
  "/billing": "billing",
  "/reports": "reports",
  "/notifications": "support",
  "/api": "api_keys",
  "/team": "users",
  "/settings": "settings",
};

export function filterNavGroupsByModules(modules: string[] | null | undefined): MerchantNavGroup[] {
  if (!modules || modules.length === 0) return MERCHANT_NAV_GROUPS;
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
