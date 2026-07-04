import type { LucideIcon } from "lucide-react";
import {
  Award,
  Bell,
  Briefcase,
  Clock,
  GraduationCap,
  LayoutDashboard,
  LifeBuoy,
  Navigation,
  User,
  Wallet,
} from "lucide-react";

export type DriverNavItem = {
  href: string;
  label: string;
  description?: string;
  icon: LucideIcon;
};

export type DriverNavGroup = {
  id: string;
  label: string;
  items: DriverNavItem[];
};

export const DRIVER_NAV_GROUPS: DriverNavGroup[] = [
  {
    id: "home",
    label: "Home",
    items: [
      {
        href: "/dashboard",
        label: "Dashboard",
        description: "KPIs, assignment, and quick actions",
        icon: LayoutDashboard,
      },
    ],
  },
  {
    id: "operations",
    label: "Operations",
    items: [
      {
        href: "/jobs",
        label: "Jobs",
        description: "Active deliveries and history",
        icon: Briefcase,
      },
      {
        href: "/navigation",
        label: "Navigation",
        description: "Maps, routes, and GPS",
        icon: Navigation,
      },
      {
        href: "/shift",
        label: "Shift",
        description: "Start, break, and availability",
        icon: Clock,
      },
      {
        href: "/communications",
        label: "Alerts",
        description: "Push, inbox, and offline sync",
        icon: Bell,
      },
    ],
  },
  {
    id: "finance",
    label: "Finance",
    items: [
      { href: "/earnings", label: "Earnings", description: "Statements and payouts", icon: Award },
      { href: "/wallet", label: "Wallet", description: "Balance and transactions", icon: Wallet },
      {
        href: "/performance",
        label: "Performance",
        description: "Ratings and metrics",
        icon: Award,
      },
    ],
  },
  {
    id: "account",
    label: "Account",
    items: [
      {
        href: "/profile",
        label: "Profile",
        description: "License, vehicle, documents",
        icon: User,
      },
      {
        href: "/training",
        label: "Training",
        description: "Modules and compliance",
        icon: GraduationCap,
      },
      {
        href: "/support",
        label: "Support",
        description: "Tickets, claims, and SOS",
        icon: LifeBuoy,
      },
    ],
  },
];

export const ALL_DRIVER_NAV_ITEMS = DRIVER_NAV_GROUPS.flatMap((g) => g.items);

export function isNavActive(pathname: string, href: string): boolean {
  if (href === "/jobs") return pathname === href || pathname.startsWith("/jobs/");
  if (href === "/navigation") return pathname.startsWith("/navigation");
  if (href === "/shift") return pathname.startsWith("/shift");
  if (href === "/communications") return pathname.startsWith("/communications");
  if (href === "/profile") return pathname.startsWith("/profile");
  return pathname === href || pathname.startsWith(`${href}/`);
}

export function activeNavLabel(pathname: string): string | null {
  const item = ALL_DRIVER_NAV_ITEMS.find((i) => isNavActive(pathname, i.href));
  return item?.label ?? null;
}
