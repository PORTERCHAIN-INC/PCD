"use client";

import { Suspense } from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import { PageSkeleton } from "@porterchain/ui/loading";
import { cn } from "@/lib/utils";
import Container from "@/components/ui/Container";
import DriverAccessGate from "@/components/DriverAccessGate";
import DriverAccountMenu from "@/components/nav/DriverAccountMenu";
import DriverAppsMenu from "@/components/nav/DriverAppsMenu";
import DriverMenuBar from "@/components/nav/DriverMenuBar";
import NotificationBell from "@/components/nav/NotificationBell";
import { DriverProfileProvider } from "@/components/nav/DriverProfileContext";
import { activeNavLabel } from "@/lib/driver-nav";
import { isPendingDriverPath } from "@/lib/onboarding";

export default function DriverShell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const pageLabel = activeNavLabel(pathname);
  const pendingOnly = isPendingDriverPath(pathname);

  if (pendingOnly) {
    return (
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
            <Suspense fallback={<PageSkeleton />}>{children}</Suspense>
          </Container>
        </div>
      </DriverAccessGate>
    );
  }

  return (
    <DriverAccessGate>
      <DriverProfileProvider>
        <div className="flex h-dvh min-w-0 flex-col overflow-x-clip bg-gray-bg">
          <header className="relative z-50 shrink-0 border-b border-primary/10 bg-white shadow-sm">
            <div className="flex min-h-12 w-full min-w-0 items-center gap-x-2 px-2 py-1.5 sm:px-3">
              <Link
                href="/dashboard"
                className="flex shrink-0 items-center gap-2 rounded-lg px-1 py-1 hover:bg-gray-bg"
              >
                <span className="flex h-8 w-8 items-center justify-center rounded-lg bg-secondary text-sm font-bold text-white shadow-sm">
                  P
                </span>
                <span className="hidden min-w-0 sm:block">
                  <span className="block text-sm font-bold leading-tight text-primary">
                    Porterchain
                  </span>
                  <span className="block text-[10px] leading-tight text-muted">Driver</span>
                </span>
              </Link>

              {pageLabel && (
                <span className="hidden max-w-[8rem] truncate rounded-md bg-primary/5 px-2 py-1 text-xs font-medium text-muted lg:inline lg:max-w-xs">
                  {pageLabel}
                </span>
              )}

              <div className="mx-0.5 hidden h-6 w-px bg-primary/10 sm:block" />

              <div className="flex min-w-0 flex-1 items-center">
                <DriverMenuBar />
              </div>

              <div className="flex shrink-0 items-center gap-2 border-l border-primary/10 pl-2">
                <NotificationBell viewAllHref="/communications" />
                <DriverAppsMenu />
                <DriverAccountMenu />
              </div>
            </div>
          </header>

          <main className={cn("min-h-0 min-w-0 flex-1 overflow-y-auto overflow-x-clip")}>
            <Container className="min-w-0 py-4 sm:py-6">
              <Suspense fallback={<PageSkeleton />}>{children}</Suspense>
            </Container>
          </main>
        </div>
      </DriverProfileProvider>
    </DriverAccessGate>
  );
}
