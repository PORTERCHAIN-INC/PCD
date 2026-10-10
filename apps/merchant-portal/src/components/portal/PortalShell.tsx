"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { RouteViewTransition } from "@porterchain/ui/view-transition";
import { cn } from "@/lib/utils";
import Container from "@/components/ui/Container";
import MerchantAccessGate from "@/components/MerchantAccessGate";
import MerchantAccountMenu from "@/components/nav/MerchantAccountMenu";
import MerchantCompanySwitcher from "@/components/nav/MerchantCompanySwitcher";
import MerchantMenuBar from "@/components/nav/MerchantMenuBar";
import NotificationBell from "@/components/nav/NotificationBell";
import ModuleGate from "@/components/portal/ModuleGate";
import MerchantLogo from "@/components/branding/MerchantLogo";
import SandboxModeBanner from "@/components/portal/SandboxModeBanner";
import { useMerchantProfile } from "@/components/nav/MerchantProfileContext";
import { useMerchantAuth } from "@/hooks/useMerchantAuth";
import { activeNavLabel } from "@/lib/merchant-nav";

function MerchantChrome({ pathname, children }: { pathname: string; children: React.ReactNode }) {
  const pageLabel = activeNavLabel(pathname);
  const { setProfile } = useMerchantProfile();
  const { session } = useMerchantAuth();

  return (
    <div className="flex h-dvh min-w-0 flex-col overflow-x-clip bg-gray-bg">
      <header className="relative z-50 shrink-0 border-b border-primary/10 bg-white shadow-sm print:hidden">
        <div className="flex min-h-12 w-full min-w-0 items-center gap-x-2 px-2 py-1.5 sm:px-3">
          <Link
            href="/dashboard"
            className="flex shrink-0 items-center gap-2 rounded-lg px-1 py-1 hover:bg-gray-bg"
          >
            <MerchantLogo src={session?.logo_url} name={session?.company_name} />
            <span className="hidden min-w-0 sm:block">
              <span className="block text-sm font-bold leading-tight text-primary">
                Porterchain
              </span>
              <span className="block text-[10px] leading-tight text-muted">
                {session?.company_name || "Merchant"}
              </span>
            </span>
          </Link>

          {pageLabel && (
            <span className="hidden max-w-[8rem] truncate rounded-md bg-primary/5 px-2 py-1 text-xs font-medium text-muted lg:inline lg:max-w-xs">
              {pageLabel}
            </span>
          )}

          <div className="mx-0.5 hidden h-6 w-px bg-primary/10 sm:block" />

          <div className="flex min-w-0 flex-1 items-center">
            <MerchantMenuBar />
          </div>

          <div className="flex shrink-0 items-center gap-2 border-l border-primary/10 pl-2">
            <MerchantCompanySwitcher compact />
            <NotificationBell viewAllHref="/notifications" />
            <MerchantAccountMenu />
          </div>
        </div>
        <SandboxModeBanner />
      </header>

      <MerchantAccessGate onProfile={setProfile}>
        <ModuleGate>
          <main
            className={cn("min-h-0 min-w-0 flex-1 overflow-y-auto overflow-x-clip py-4 sm:py-6")}
          >
            <Container className="min-w-0">
              <RouteViewTransition>{children}</RouteViewTransition>
            </Container>
          </main>
        </ModuleGate>
      </MerchantAccessGate>
    </div>
  );
}

export default function PortalShell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  return <MerchantChrome pathname={pathname}>{children}</MerchantChrome>;
}
