import PortalShell from "@/components/portal/PortalShell";
import { MerchantProfileProvider } from "@/components/nav/MerchantProfileContext";
import { Suspense } from "react";

export default function PortalLayout({ children }: { children: React.ReactNode }) {
  return (
    <MerchantProfileProvider>
      <Suspense fallback={<div className="min-h-dvh bg-gray-bg" />}>
        <PortalShell>{children}</PortalShell>
      </Suspense>
    </MerchantProfileProvider>
  );
}
