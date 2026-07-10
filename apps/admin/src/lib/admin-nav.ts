import type { LucideIcon } from "lucide-react";
import {
  BarChart3,
  Building2,
  ClipboardList,
  CreditCard,
  FlaskConical,
  Headphones,
  Bell,
  HeartPulse,
  LayoutDashboard,
  Map,
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
        label: "Leads",
        description: "Website inquiries & contact forms",
        icon: UserPlus,
      },
      {
        href: "/merchants",
        label: "Merchants",
        description: "B2B accounts & contracts",
        icon: Building2,
      },
      { href: "/drivers", label: "Drivers", description: "Fleet & compliance", icon: Truck },
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

export function isNavActive(pathname: string, href: string): boolean {
  return pathname === href || pathname.startsWith(`${href}/`);
}

export function activeNavLabel(pathname: string): string | null {
  const item = ALL_ADMIN_NAV_ITEMS.find((i) => isNavActive(pathname, i.href));
  return item?.label ?? null;
}
