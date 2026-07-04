import PortalShell from "@/components/portal/PortalShell";
import { MerchantProfileProvider } from "@/components/nav/MerchantProfileContext";
import { GoogleMapsProvider } from "@porterchain/maps";
import { publicEnv } from "@/lib/env";

export const dynamic = "force-dynamic";

export default function PortalLayout({ children }: { children: React.ReactNode }) {
  return (
    <GoogleMapsProvider apiKey={publicEnv.googleMapsApiKey}>
      <MerchantProfileProvider>
        <PortalShell>{children}</PortalShell>
      </MerchantProfileProvider>
    </GoogleMapsProvider>
  );
}
