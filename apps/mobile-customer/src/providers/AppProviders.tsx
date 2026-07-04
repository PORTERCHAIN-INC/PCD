import { type ReactNode } from "react";
import { QueryClientProvider } from "@tanstack/react-query";
import { SafeAreaProvider } from "react-native-safe-area-context";
import { createMobileQueryClient } from "@porterchain/mobile-api";
import { MapsProvider } from "@porterchain/mobile-maps";
import { ThemeProvider } from "@porterchain/mobile-theme";
import { MobileUiProvider, ToastProvider } from "@porterchain/mobile-ui";
import { CustomerApiProvider } from "../api/CustomerApiContext";
import { NotificationLayer } from "./NotificationLayer";
import { OfflineSyncLayer } from "./OfflineSyncLayer";
import { PerformanceLayer } from "./PerformanceLayer";
import { SecurityLayer } from "./SecurityLayer";
import { mobileEnv } from "../config/env";

const queryClient = createMobileQueryClient();

export function AppProviders({ children }: { children: ReactNode }) {
  return (
    <SafeAreaProvider>
      <ThemeProvider initialScheme="system">
        <QueryClientProvider client={queryClient}>
          <PerformanceLayer>
            <MapsProvider googleMapsApiKey={mobileEnv.googleMapsApiKey}>
              <MobileUiProvider>
                <ToastProvider>
                  <SecurityLayer>
                    <CustomerApiProvider>
                      <OfflineSyncLayer>
                        <NotificationLayer>{children}</NotificationLayer>
                      </OfflineSyncLayer>
                    </CustomerApiProvider>
                  </SecurityLayer>
                </ToastProvider>
              </MobileUiProvider>
            </MapsProvider>
          </PerformanceLayer>
        </QueryClientProvider>
      </ThemeProvider>
    </SafeAreaProvider>
  );
}
