import { useMemo, type ReactNode } from "react";
import { OfflineSyncProvider, createDriverOfflineSyncAdapter } from "@porterchain/mobile-offline";
import { useDriverApi } from "../api/DriverApiContext";

export function OfflineSyncLayer({ children }: { children: ReactNode }) {
  const api = useDriverApi();
  const adapter = useMemo(() => createDriverOfflineSyncAdapter(api), [api]);

  return (
    <OfflineSyncProvider
      storeId="porterchain-driver-offline"
      adapter={adapter}
      autoSyncIntervalMs={30000}
      enableBackgroundGps
      mode="driver"
    >
      {children}
    </OfflineSyncProvider>
  );
}
