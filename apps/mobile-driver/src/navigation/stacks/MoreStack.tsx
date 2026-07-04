import { createNativeStackNavigator } from "@react-navigation/native-stack";
import { createLazyScreen } from "@porterchain/mobile-performance";
import { MoreScreen } from "../../screens/more/MoreScreen";
import { ProfileScreen } from "../../screens/more/ProfileScreen";
import { NotificationsScreen } from "../../screens/more/NotificationsScreen";
import { SupportScreen } from "../../screens/more/SupportScreen";
import { SettingsScreen } from "../../screens/more/SettingsScreen";
import type { MoreStackParamList } from "../types";

const OfflineSyncScreen = createLazyScreen(() => import("../../screens/more/OfflineSyncScreen"), "OfflineSyncScreen");
const SosScreen = createLazyScreen(() => import("../../screens/more/SosScreen"), "SosScreen");
const PerformanceScreen = createLazyScreen(() => import("../../screens/more/PerformanceScreen"), "PerformanceScreen");

const Stack = createNativeStackNavigator<MoreStackParamList>();

export function MoreStack() {
  return (
    <Stack.Navigator screenOptions={{ headerShown: false, freezeOnBlur: true }}>
      <Stack.Screen name="More" component={MoreScreen} />
      <Stack.Screen name="Profile" component={ProfileScreen} />
      <Stack.Screen name="Notifications" component={NotificationsScreen} />
      <Stack.Screen name="OfflineSync" component={OfflineSyncScreen as never} />
      <Stack.Screen name="Support" component={SupportScreen} />
      <Stack.Screen name="Sos" component={SosScreen as never} />
      <Stack.Screen name="Settings" component={SettingsScreen} />
      <Stack.Screen name="Performance" component={PerformanceScreen as never} />
    </Stack.Navigator>
  );
}
