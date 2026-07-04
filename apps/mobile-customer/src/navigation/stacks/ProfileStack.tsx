import { createNativeStackNavigator } from "@react-navigation/native-stack";
import { createLazyScreen } from "@porterchain/mobile-performance";
import { ProfileScreen } from "../../screens/profile/ProfileScreen";
import { InvoicesScreen } from "../../screens/profile/InvoicesScreen";
import { ReceiptsScreen } from "../../screens/profile/ReceiptsScreen";
import { SupportScreen } from "../../screens/profile/SupportScreen";
import { SettingsScreen } from "../../screens/profile/SettingsScreen";
import type { ProfileStackParamList } from "../types";

const ClaimsScreen = createLazyScreen(() => import("../../screens/profile/ClaimsScreen"), "ClaimsScreen");
const OfflineSyncScreen = createLazyScreen(() => import("../../screens/profile/OfflineSyncScreen"), "OfflineSyncScreen");
const PerformanceScreen = createLazyScreen(() => import("../../screens/profile/PerformanceScreen"), "PerformanceScreen");

const Stack = createNativeStackNavigator<ProfileStackParamList>();

export function ProfileStack() {
  return (
    <Stack.Navigator screenOptions={{ headerShown: false, freezeOnBlur: true }}>
      <Stack.Screen name="Profile" component={ProfileScreen} />
      <Stack.Screen name="Invoices" component={InvoicesScreen} />
      <Stack.Screen name="Receipts" component={ReceiptsScreen} />
      <Stack.Screen name="Support" component={SupportScreen} />
      <Stack.Screen name="Claims" component={ClaimsScreen as never} />
      <Stack.Screen name="OfflineSync" component={OfflineSyncScreen as never} />
      <Stack.Screen name="Settings" component={SettingsScreen} />
      <Stack.Screen name="Performance" component={PerformanceScreen as never} />
    </Stack.Navigator>
  );
}
