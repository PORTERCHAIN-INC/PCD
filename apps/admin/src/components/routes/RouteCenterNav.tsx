"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useMemo } from "react";
import {
  BarChart3,
  ChevronDown,
  ClipboardList,
  History,
  LayoutDashboard,
  Map,
  Radio,
  Route,
  Send,
  Sparkles,
  Wrench,
} from "lucide-react";
import { cn } from "@porterchain/ui/utils";

const ROUTE_SEGMENTS = new Set([
  "planning-queue",
  "builder",
  "optimization",
  "dispatch",
  "live",
  "analytics",
  "history",
  "templates",
]);

export const ROUTE_NAV_GROUPS = [
  {
    label: "Overview",
    items: [{ href: "/routes", label: "Dashboard", icon: LayoutDashboard, exact: true }],
  },
  {
    label: "Plan & Build",
    items: [
      { href: "/routes/planning-queue", label: "Planning Queue", icon: ClipboardList },
      { href: "/routes/builder", label: "Route Builder", icon: Wrench },
      { href: "/routes/templates", label: "Templates", icon: Route },
    ],
  },
  {
    label: "Optimize & Dispatch",
    items: [
      { href: "/routes/optimization", label: "Optimization", icon: Sparkles },
      { href: "/routes/dispatch", label: "Dispatch", icon: Send },
    ],
  },
  {
    label: "Execute & Analyze",
    items: [
      { href: "/routes/live", label: "Live Execution", icon: Radio },
      { href: "/routes/analytics", label: "Analytics", icon: BarChart3 },
      { href: "/routes/history", label: "History", icon: History },
    ],
  },
] as const;

type NavItem = {
  href: string;
  label: string;
  icon: typeof LayoutDashboard;
  exact?: boolean;
};

const ALL_TABS: NavItem[] = ROUTE_NAV_GROUPS.flatMap((g) => [...g.items]);

function isRoute360Path(pathname: string) {
  const parts = pathname.split("/").filter(Boolean);
  return parts[0] === "routes" && parts.length === 2 && !ROUTE_SEGMENTS.has(parts[1]!);
}

function isActive(pathname: string, href: string, exact?: boolean) {
  if (exact) return pathname === href;
  return pathname === href || pathname.startsWith(`${href}/`);
}

export default function RouteCenterNav() {
  const pathname = usePathname();

  const isDetail = isRoute360Path(pathname);
  const activeTab = useMemo(
    () => ALL_TABS.find((tab) => isActive(pathname, tab.href, "exact" in tab ? tab.exact : false)),
    [pathname]
  );

  if (isDetail) return null;

  return (
    <div className="space-y-3">
      {/* Mobile: compact select */}
      <div className="md:hidden">
        <label className="sr-only" htmlFor="route-center-nav-mobile">
          Route Center section
        </label>
        <div className="relative">
          <select
            id="route-center-nav-mobile"
            value={activeTab?.href ?? "/routes"}
            onChange={(e) => {
              window.location.href = e.target.value;
            }}
            className="w-full appearance-none rounded-xl border border-primary/15 bg-white py-2.5 pl-3 pr-10 text-sm font-medium text-primary"
          >
            {ROUTE_NAV_GROUPS.map((group) => (
              <optgroup key={group.label} label={group.label}>
                {group.items.map((item) => (
                  <option key={item.href} value={item.href}>
                    {item.label}
                  </option>
                ))}
              </optgroup>
            ))}
          </select>
          <ChevronDown className="pointer-events-none absolute right-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted" />
        </div>
        <Link
          href="/live-map"
          className="mt-2 flex items-center justify-center gap-2 rounded-xl border border-primary/10 bg-white px-3 py-2 text-sm font-medium text-primary/80 hover:bg-gray-bg"
        >
          <Map className="h-4 w-4" />
          Open Fleet Map
        </Link>
      </div>

      {/* Desktop: grouped tabs */}
      <div className="hidden md:block">
        <div className="flex flex-wrap items-end justify-between gap-3">
          <div className="flex min-w-0 flex-1 flex-wrap gap-x-6 gap-y-3">
            {ROUTE_NAV_GROUPS.map((group) => (
              <div key={group.label} className="min-w-0">
                <p className="mb-1.5 px-1 text-[0.65rem] font-bold uppercase tracking-wider text-muted">
                  {group.label}
                </p>
                <div className="flex flex-wrap gap-1">
                  {group.items.map((item) => {
                    const { href, label, icon: Icon } = item;
                    const exact = "exact" in item ? item.exact : false;
                    const active = isActive(pathname, href, exact);
                    return (
                      <Link
                        key={href}
                        href={href}
                        className={cn(
                          "flex items-center gap-1.5 rounded-xl px-3 py-2 text-sm font-medium transition-colors",
                          active
                            ? "bg-secondary text-white shadow-sm"
                            : "text-primary/70 hover:bg-white hover:text-primary"
                        )}
                      >
                        <Icon className="h-4 w-4 shrink-0" />
                        <span className="whitespace-nowrap">{label}</span>
                      </Link>
                    );
                  })}
                </div>
              </div>
            ))}
          </div>
          <Link
            href="/live-map"
            className="flex shrink-0 items-center gap-2 rounded-xl border border-primary/10 bg-white px-3 py-2 text-sm font-medium text-primary/70 hover:border-secondary/30 hover:text-secondary"
          >
            <Map className="h-4 w-4" />
            Fleet Map
          </Link>
        </div>
      </div>
    </div>
  );
}
