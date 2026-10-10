"use client";

import { Suspense, useCallback, useMemo } from "react";
import Link from "next/link";
import { usePathname, useRouter, useSearchParams } from "next/navigation";
import Container from "@porterchain/ui/container";
import { AppShell, type AppNavGroup, type PaletteEntry } from "@porterchain/ui/app-nav";
import { RouteViewTransition } from "@porterchain/ui/view-transition";
import {
  ADMIN_PALETTE_EXTRA,
  activeNavLabel,
  adminNavForRole,
  isNavActive,
  type AdminBadgeKey,
} from "@/lib/admin-nav";
import { SECTION_DESCRIPTIONS } from "@/lib/settings-metadata";
import { useAdminAuth } from "@/hooks/useAdminAuth";
import { useAdminNavBadges } from "@/hooks/useAdminNavBadges";
import { ops } from "@/lib/operations";
import AdminAccessGate from "@/components/AdminAccessGate";
import AdminAccountMenu from "@/components/nav/AdminAccountMenu";
import AdminAppsMenu from "@/components/nav/AdminAppsMenu";
import { useOptionalAdminProfile } from "@/components/nav/AdminProfileContext";
import NotificationBell from "@/components/nav/NotificationBell";

const titleCase = (s: string) => s.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase());

const SETTINGS_PALETTE: PaletteEntry[] = Object.entries(SECTION_DESCRIPTIONS).map(([id, d]) => ({
  href: `/settings?section=${id}`,
  label: `Settings › ${titleCase(id)}`,
  group: "Settings",
  keywords: d,
}));

function Shell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const searchParams = useSearchParams();
  const router = useRouter();
  const search = searchParams.toString() ? `?${searchParams.toString()}` : "";
  const profile = useOptionalAdminProfile();
  const { getApiToken } = useAdminAuth();

  const base = useMemo(() => adminNavForRole(profile?.role), [profile?.role]);
  const keys = useMemo(
    () => base.flatMap((g) => g.items.map((i) => i.badgeKey)).filter(Boolean) as AdminBadgeKey[],
    [base]
  );
  const badges = useAdminNavBadges(keys);
  const groups: AppNavGroup[] = useMemo(
    () =>
      base.map((g) => ({
        id: g.id,
        label: g.id === "dashboard" ? "" : g.label,
        items: g.items.map((i) => ({ ...i, badge: i.badgeKey ? badges[i.badgeKey] : undefined })),
      })),
    [base, badges]
  );
  const visible = useMemo(() => new Set(base.map((g) => g.id)), [base]);
  const palette = useMemo(
    () => [
      ...ADMIN_PALETTE_EXTRA,
      ...(visible.has("administration") &&
      base.some((g) => g.items.some((i) => i.href === "/settings"))
        ? SETTINGS_PALETTE
        : []),
    ],
    [base, visible]
  );
  const liveSearch = useCallback(
    async (q: string): Promise<PaletteEntry[]> => {
      const r = await ops.search(await getApiToken(), q);
      return [
        ...r.orders.slice(0, 6).map((o) => ({
          href: `/orders/${o.id}`,
          label: o.tracking_number || o.order_number,
          group: "Orders",
          hint: `Order · ${titleCase(o.state.toLowerCase())}`,
        })),
        ...r.drivers.slice(0, 4).map((d) => ({
          href: `/drivers/${d.id}`,
          label: d.name,
          group: "Drivers",
          hint: d.online ? "Driver · online" : "Driver",
        })),
      ];
    },
    [getApiToken]
  );

  return (
    <AppShell
      brand={{
        mark: "P",
        name: "Porterchain",
        sub: profile?.role === "super_admin" ? "Super admin" : "Admin",
      }}
      brandHref="/dashboard"
      groups={groups}
      isActive={(href) => isNavActive(pathname, href, search)}
      Link={Link}
      navigate={(href) => router.push(href as never)}
      title={activeNavLabel(pathname, search)}
      palette={palette}
      search={liveSearch}
      storageKey="pc.admin.nav.collapsed"
      mainClassName="ops-main"
      actions={
        <>
          <AdminAppsMenu />
          <NotificationBell viewAllHref="/notifications" />
          <AdminAccountMenu />
        </>
      }
    >
      {/* Fluid rail — every ops page uses full viewport width for tables/KPIs. */}
      <Container width="fluid" className="admin-page-rail min-w-0">
        <RouteViewTransition>{children}</RouteViewTransition>
      </Container>
    </AppShell>
  );
}

export default function AdminShell({ children }: { children: React.ReactNode }) {
  // Access gate wraps the shell so the nav sees the real admin_users role
  // (super_admin / admin / …) and can hide what that role can't use.
  return (
    <AdminAccessGate>
      <Suspense fallback={null}>
        <Shell>{children}</Shell>
      </Suspense>
    </AdminAccessGate>
  );
}
