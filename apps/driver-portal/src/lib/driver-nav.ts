import type { LucideIcon } from "lucide-react";
import {
  Briefcase,
  Car,
  Clock,
  FileText,
  GraduationCap,
  LayoutDashboard,
  LifeBuoy,
  Navigation,
  Route,
  Siren,
  TrendingUp,
  User,
  Wallet,
  Banknote,
} from "lucide-react";

export type DriverNavItem = {
  href: string;
  label: string;
  description?: string;
  icon: LucideIcon;
  badgeKey?: "jobs";
};

export type DriverNavGroup = {
  id: string;
  label: string;
  items: DriverNavItem[];
};

/**
 * Ordered by a driver's day: today → jobs → route → navigate → shift, then pay, then me.
 * Alerts live on the bell (no duplicate item); extra pages stay reachable via ⌘K.
 */
export const DRIVER_NAV_GROUPS: DriverNavGroup[] = [
  {
    id: "home",
    label: "",
    items: [
      {
        href: "/dashboard",
        label: "Today",
        description: "Shift, next stop, earnings",
        icon: LayoutDashboard,
      },
      {
        href: "/jobs",
        label: "Jobs",
        description: "Current and upcoming jobs",
        icon: Briefcase,
        badgeKey: "jobs",
      },
      { href: "/route", label: "Route", description: "Stops in order", icon: Route },
      {
        href: "/navigation",
        label: "Navigate",
        description: "Turn-by-turn to next stop",
        icon: Navigation,
      },
      { href: "/shift", label: "Shift", description: "Clock in, breaks, end of day", icon: Clock },
    ],
  },
  {
    id: "finance",
    label: "Pay",
    items: [
      {
        href: "/earnings",
        label: "Earnings",
        description: "Statements and payouts",
        icon: Banknote,
      },
      { href: "/wallet", label: "Wallet", description: "Balance and transactions", icon: Wallet },
    ],
  },
  {
    id: "account",
    label: "Me",
    items: [
      {
        href: "/performance",
        label: "Performance",
        description: "On-time, ratings, tier",
        icon: TrendingUp,
      },
      {
        href: "/vehicle",
        label: "Vehicle",
        description: "Vehicle, photos, capabilities",
        icon: Car,
      },
      {
        href: "/documents",
        label: "Documents",
        description: "Licence, insurance, expiry",
        icon: FileText,
      },
      {
        href: "/training",
        label: "Training",
        description: "Courses and certificates",
        icon: GraduationCap,
      },
      { href: "/profile", label: "Profile", description: "Contact, bank, preferences", icon: User },
      { href: "/support", label: "Support", description: "Help and tickets", icon: LifeBuoy },
      {
        href: "/emergency",
        label: "Emergency",
        description: "Incident, roadside, SOS",
        icon: Siren,
      },
    ],
  },
];

export const DRIVER_PALETTE_EXTRA = [
  {
    href: "/communications",
    label: "Alerts & messages",
    group: "Me",
    keywords: "notifications bell",
  },
  { href: "/stops", label: "Stops", group: "Today" },
  { href: "/insurance", label: "Insurance", group: "Me" },
  {
    href: "/monitoring-policy",
    label: "GPS monitoring policy",
    group: "Me",
    keywords: "privacy location",
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
