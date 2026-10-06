import PortalShell from "@/components/portal/PortalShell";
import { MerchantProfileProvider } from "@/components/nav/MerchantProfileContext";

export default function PortalLayout({ children }: { children: React.ReactNode }) {
  return (
    <MerchantProfileProvider>
      <PortalShell>{children}</PortalShell>
    </MerchantProfileProvider>
  );
}
