import { createNativeStackNavigator } from "@react-navigation/native-stack";
import { createLazyScreen } from "@porterchain/mobile-performance";
import { TrackingScreen } from "../../screens/tracking/TrackingScreen";
import { HistoryScreen } from "../../screens/tracking/HistoryScreen";
import type { TrackingStackParamList } from "../types";

const LiveMapScreen = createLazyScreen(() => import("../../screens/tracking/LiveMapScreen"), "LiveMapScreen");

const Stack = createNativeStackNavigator<TrackingStackParamList>();

export function TrackingStack() {
  return (
    <Stack.Navigator screenOptions={{ headerShown: false, freezeOnBlur: true }}>
      <Stack.Screen name="Tracking" component={TrackingScreen} />
      <Stack.Screen name="LiveMap" component={LiveMapScreen as never} />
      <Stack.Screen name="History" component={HistoryScreen} />
    </Stack.Navigator>
  );
}
