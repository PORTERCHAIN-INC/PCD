import { useMemo, type ReactNode } from "react";
import { OfflineSyncProvider, createCustomerOfflineSyncAdapter } from "@porterchain/mobile-offline";
import { useCustomerApi } from "../api/CustomerApiContext";

export function OfflineSyncLayer({ children }: { children: ReactNode }) {
  const api = useCustomerApi();
  const adapter = useMemo(() => createCustomerOfflineSyncAdapter(api), [api]);

  return (
    <OfflineSyncProvider storeId="porterchain-customer-offline" adapter={adapter} autoSyncIntervalMs={45000} mode="customer">
      {children}
    </OfflineSyncProvider>
  );
}
