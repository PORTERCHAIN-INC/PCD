"use client";

import Link from "next/link";
import { usePathname, useSearchParams } from "next/navigation";
import Container from "@porterchain/ui/container";
import { cn } from "@porterchain/ui/utils";
import { activeNavLabel } from "@/lib/admin-nav";
import AdminAccessGate from "@/components/AdminAccessGate";
import AdminAccountMenu from "@/components/nav/AdminAccountMenu";
import AdminAppsMenu from "@/components/nav/AdminAppsMenu";
import AdminMenuBar from "@/components/nav/AdminMenuBar";
import OpenFleetbaseButton from "@/components/nav/OpenFleetbaseButton";
import NotificationBell from "@/components/nav/NotificationBell";

export default function AdminShell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const searchParams = useSearchParams();
  const search = searchParams.toString() ? `?${searchParams.toString()}` : "";
  const pageLabel = activeNavLabel(pathname, search);

  // Access gate wraps header + main so the account menu always has the real
  // admin_users role (super_admin / admin / …), not a fake "staff" fallback.
  return (
    <AdminAccessGate>
      <div className="flex h-dvh flex-col bg-gray-bg">
        <header className="relative z-50 shrink-0 overflow-visible border-b border-primary/10 bg-white shadow-sm">
          <div className="flex min-h-12 flex-wrap items-center gap-x-2 gap-y-1 px-2 py-1.5 sm:px-3">
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

            {pageLabel && (
              <span className="hidden max-w-[8rem] truncate rounded-md bg-primary/5 px-2 py-1 text-xs font-medium text-muted sm:inline lg:max-w-xs">
                {pageLabel}
              </span>
            )}

            <div className="mx-0.5 hidden h-6 w-px bg-primary/10 sm:block" />

            <div className="flex min-w-0 flex-1 items-center">
              <AdminMenuBar />
            </div>

            <div className="flex shrink-0 items-center gap-1.5 border-l border-primary/10 pl-2 sm:gap-2">
              <OpenFleetbaseButton variant="header" />
              <AdminAppsMenu />
              <NotificationBell viewAllHref="/notifications" />
              <AdminAccountMenu />
            </div>
          </div>
        </header>

        <main className={cn("ops-main min-h-0 flex-1 overflow-auto", "py-6")}>
          <Container>{children}</Container>
        </main>
      </div>
    </AdminAccessGate>
  );
}
