import type { PropsWithChildren } from "react";
import { View } from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";
import { OfflineSyncBar } from "@porterchain/mobile-offline";
import { Screen } from "@porterchain/mobile-ui";

export function AppShell({ children }: PropsWithChildren) {
  return (
    <Screen>
      <SafeAreaView edges={["top"]} style={{ flex: 1 }}>
        <OfflineSyncBar />
        <View style={{ flex: 1 }}>{children}</View>
      </SafeAreaView>
    </Screen>
  );
}
