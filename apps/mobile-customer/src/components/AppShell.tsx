import type { PropsWithChildren } from "react";
import { View } from "react-native";
import { OfflineSyncBar } from "@porterchain/mobile-offline";
import { Screen } from "@porterchain/mobile-ui";

export function AppShell({ children }: PropsWithChildren) {
  return (
    <Screen>
      <View>
        <OfflineSyncBar />
      </View>
      {children}
    </Screen>
  );
}
