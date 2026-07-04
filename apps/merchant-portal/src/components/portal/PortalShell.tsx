"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { cn } from "@/lib/utils";
import Container from "@/components/ui/Container";
import MerchantAccessGate from "@/components/MerchantAccessGate";
import MerchantAccountMenu from "@/components/nav/MerchantAccountMenu";
import MerchantMenuBar from "@/components/nav/MerchantMenuBar";
import { useMerchantProfile } from "@/components/nav/MerchantProfileContext";
import { activeNavLabel } from "@/lib/merchant-nav";

export default function PortalShell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const pageLabel = activeNavLabel(pathname);
  const { setProfile } = useMerchantProfile();

  return (
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
              <span className="block text-[10px] leading-tight text-muted">Merchant</span>
            </span>
          </Link>

          {pageLabel && (
            <span className="hidden max-w-[8rem] truncate rounded-md bg-primary/5 px-2 py-1 text-xs font-medium text-muted sm:inline lg:max-w-xs">
              {pageLabel}
            </span>
          )}

          <div className="mx-0.5 hidden h-6 w-px bg-primary/10 sm:block" />

          <div className="flex min-w-0 flex-1 items-center">
            <MerchantMenuBar />
          </div>

          <div className="flex shrink-0 items-center gap-2 border-l border-primary/10 pl-2">
            <MerchantAccountMenu />
          </div>
        </div>
      </header>

      <MerchantAccessGate onProfile={setProfile}>
        <main className={cn("min-h-0 flex-1 overflow-auto py-6")}>
          <Container>{children}</Container>
        </main>
      </MerchantAccessGate>
    </div>
  );
}
