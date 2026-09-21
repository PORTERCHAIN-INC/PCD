"use client";

import { Suspense } from "react";
import Link from "next/link";
import { usePathname, useSearchParams } from "next/navigation";
import Container from "@porterchain/ui/container";
import { cn } from "@porterchain/ui/utils";
import { activeNavLabel } from "@/lib/admin-nav";
import AdminAccessGate from "@/components/AdminAccessGate";
import AdminAccountMenu from "@/components/nav/AdminAccountMenu";
import AdminAppsMenu from "@/components/nav/AdminAppsMenu";
import AdminMenuBar from "@/components/nav/AdminMenuBar";
import NotificationBell from "@/components/nav/NotificationBell";

function HeaderPageLabel({ pathname }: { pathname: string }) {
  const searchParams = useSearchParams();
  const search = searchParams.toString() ? `?${searchParams.toString()}` : "";
  const pageLabel = activeNavLabel(pathname, search);
  if (!pageLabel) return null;
  return (
    <span className="hidden max-w-[8rem] truncate rounded-md bg-primary/5 px-2 py-1 text-xs font-medium text-muted lg:inline lg:max-w-xs">
      {pageLabel}
    </span>
  );
}

export default function AdminShell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();

  // Access gate wraps header + main so the account menu always has the real
  // admin_users role (super_admin / admin / …), not a fake "staff" fallback.
  return (
    <AdminAccessGate>
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
                <span className="block text-[10px] leading-tight text-muted">Admin</span>
              </span>
            </Link>

            <Suspense fallback={null}>
              <HeaderPageLabel pathname={pathname} />
            </Suspense>

            <div className="mx-0.5 hidden h-6 w-px bg-primary/10 sm:block" />

            <div className="flex min-w-0 flex-1 items-center">
              <AdminMenuBar />
            </div>

            <div className="flex shrink-0 items-center gap-1 border-l border-primary/10 pl-2 sm:gap-2">
              <AdminAppsMenu />
              <NotificationBell viewAllHref="/notifications" />
              <AdminAccountMenu />
            </div>
          </div>
        </header>

        <main className={cn("ops-main min-h-0 min-w-0 flex-1 overflow-y-auto overflow-x-clip")}>
          <Container className="min-w-0">{children}</Container>
        </main>
      </div>
    </AdminAccessGate>
  );
}
