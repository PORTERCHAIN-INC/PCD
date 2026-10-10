"use client";

import { createContext, Suspense, useContext, useMemo } from "react";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useQuery } from "@tanstack/react-query";
import { PageSkeleton } from "@porterchain/ui/loading";
import { RouteViewTransition } from "@porterchain/ui/view-transition";
import Container from "@/components/ui/Container";
import DriverAccessGate from "@/components/DriverAccessGate";
import DriverAccountMenu from "@/components/nav/DriverAccountMenu";
import DriverAppsMenu from "@/components/nav/DriverAppsMenu";
import NotificationBell from "@/components/nav/NotificationBell";
import { DriverProfileProvider } from "@/components/nav/DriverProfileContext";
import { AppShell, type AppNavGroup } from "@porterchain/ui/app-nav";
import { driverApi } from "@/lib/api";
import {
  DRIVER_NAV_GROUPS,
  DRIVER_PALETTE_EXTRA,
  activeNavLabel,
  isNavActive,
} from "@/lib/driver-nav";
import { isPendingDriverPath } from "@/lib/onboarding";

const DriverShellContext = createContext(false);

export default function DriverShell({ children }: { children: React.ReactNode }) {
  const nested = useContext(DriverShellContext);
  const pathname = usePathname();
  if (nested) return children;
  const pendingOnly = isPendingDriverPath(pathname);

  if (pendingOnly) {
    return (
      <DriverShellContext.Provider value={true}>
        <DriverAccessGate>
          <div className="min-h-dvh bg-gray-bg">
            <header className="border-b border-primary/10 bg-white">
              <div className="mx-auto flex max-w-5xl items-center justify-between gap-4 px-4 py-3">
                <Link href="/onboarding" className="text-sm font-semibold text-secondary">
                  ← Back to activation
                </Link>
                <span className="text-xs text-muted">Documents only — dashboard locked</span>
              </div>
            </header>
            <Container className="py-6">
              <Suspense fallback={<PageSkeleton />}>
                <RouteViewTransition>{children}</RouteViewTransition>
              </Suspense>
            </Container>
          </div>
        </DriverAccessGate>
      </DriverShellContext.Provider>
    );
  }

  return (
    <DriverShellContext.Provider value={true}>
      <DriverAccessGate>
        <DriverProfileProvider>
          <DriverChrome>{children}</DriverChrome>
        </DriverProfileProvider>
      </DriverAccessGate>
    </DriverShellContext.Provider>
  );
}

function DriverChrome({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const router = useRouter();
  // Same key/shape as useDriverJobs, so the Jobs badge shares its cache.
  const { data } = useQuery({
    queryKey: ["driver-jobs"],
    queryFn: async () => ({ jobs: await driverApi.jobs(), at: new Date() }),
    refetchInterval: 60_000,
  });
  const jobs = data ? (data.jobs.current ? 1 : 0) + data.jobs.upcoming.length : 0;
  const groups: AppNavGroup[] = useMemo(
    () =>
      DRIVER_NAV_GROUPS.map((g) => ({
        ...g,
        items: g.items.map((i) => ({ ...i, badge: i.badgeKey === "jobs" ? jobs : undefined })),
      })),
    [jobs]
  );
  const tabs = useMemo(() => {
    const flat = groups.flatMap((g) => g.items);
    return ["/dashboard", "/jobs", "/route", "/earnings"].map((h) =>
      flat.find((i) => i.href === h)!
    );
  }, [groups]);

  return (
    <AppShell
      brand={{ mark: "P", name: "Porterchain", sub: "Driver" }}
      brandHref="/dashboard"
      groups={groups}
      isActive={(href) => isNavActive(pathname, href)}
      Link={Link}
      navigate={(href) => router.push(href as never)}
      title={activeNavLabel(pathname)}
      palette={DRIVER_PALETTE_EXTRA}
      bottomTabs={tabs}
      storageKey="pc.driver.nav.collapsed"
      actions={
        <>
          <NotificationBell viewAllHref="/communications" />
          <DriverAppsMenu />
          <DriverAccountMenu />
        </>
      }
    >
      <Container className="min-w-0 py-4 sm:py-6">
        <Suspense fallback={<PageSkeleton />}>
          <RouteViewTransition>{children}</RouteViewTransition>
        </Suspense>
      </Container>
    </AppShell>
  );
}
