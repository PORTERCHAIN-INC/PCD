"use client";

import { Suspense, useMemo } from "react";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useQuery } from "@tanstack/react-query";
import { AppShell, type AppNavGroup } from "@porterchain/ui/app-nav";
import { RouteViewTransition } from "@porterchain/ui/view-transition";
import Container from "@/components/ui/Container";
import MerchantAccessGate from "@/components/MerchantAccessGate";
import MerchantAccountMenu from "@/components/nav/MerchantAccountMenu";
import MerchantCompanySwitcher from "@/components/nav/MerchantCompanySwitcher";
import NotificationBell from "@/components/nav/NotificationBell";
import ModuleGate from "@/components/portal/ModuleGate";
import MerchantLogo from "@/components/branding/MerchantLogo";
import SandboxModeBanner from "@/components/portal/SandboxModeBanner";
import { useMerchantProfile } from "@/components/nav/MerchantProfileContext";
import { useMerchantAuth } from "@/hooks/useMerchantAuth";
import { getDashboard } from "@/lib/api";
import {
  MERCHANT_PALETTE_EXTRA,
  activeNavLabel,
  filterNavGroupsByModules,
  isNavActive,
} from "@/lib/merchant-nav";

function MerchantChrome({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const router = useRouter();
  const { setProfile } = useMerchantProfile();
  const { session, modules, getApiToken, orgId, isLoaded, isSignedIn } = useMerchantAuth();

  // Same query key as Home, so the badge costs no extra request there.
  const { data: dash } = useQuery({
    queryKey: ["merchant-dashboard", orgId ?? null],
    enabled: Boolean(isLoaded && isSignedIn && orgId),
    refetchInterval: 120_000,
    queryFn: async () => getDashboard(await getApiToken(), orgId),
  });

  const groups: AppNavGroup[] = useMemo(
    () =>
      filterNavGroupsByModules(modules).map((g) => ({
        ...g,
        items: g.items.map((i) => ({
          ...i,
          badge:
            i.badgeKey === "invoices"
              ? dash?.invoices_due
              : i.badgeKey === "tickets"
                ? dash?.open_support_tickets
                : undefined,
        })),
      })),
    [modules, dash]
  );
  const tabs = useMemo(() => {
    const flat = groups.flatMap((g) => g.items);
    return ["/dashboard", "/book", "/orders", "/billing"]
      .map((h) => flat.find((i) => i.href === h))
      .filter((i): i is NonNullable<typeof i> => Boolean(i));
  }, [groups]);

  return (
    <AppShell
      brand={{
        mark: "P",
        name: "Porterchain",
        sub: session?.company_name || "Merchant",
        logo: <MerchantLogo src={session?.logo_url} name={session?.company_name} />,
      }}
      brandHref="/dashboard"
      groups={groups}
      isActive={(href) => isNavActive(pathname, href)}
      Link={Link}
      navigate={(href) => router.push(href as never)}
      title={activeNavLabel(pathname)}
      palette={MERCHANT_PALETTE_EXTRA}
      bottomTabs={tabs}
      storageKey="pc.merchant.nav.collapsed"
      banner={<SandboxModeBanner />}
      mainClassName="py-4 sm:py-6 print:overflow-visible"
      actions={
        <>
          <MerchantCompanySwitcher compact />
          <NotificationBell viewAllHref="/notifications" />
          <MerchantAccountMenu />
        </>
      }
    >
      <MerchantAccessGate onProfile={setProfile}>
        <ModuleGate>
          <Container className="min-w-0">
            <RouteViewTransition>{children}</RouteViewTransition>
          </Container>
        </ModuleGate>
      </MerchantAccessGate>
    </AppShell>
  );
}

export default function PortalShell({ children }: { children: React.ReactNode }) {
  return (
    <Suspense fallback={null}>
      <MerchantChrome>{children}</MerchantChrome>
    </Suspense>
  );
}
