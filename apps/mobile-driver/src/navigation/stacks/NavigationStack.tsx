import { createNativeStackNavigator } from "@react-navigation/native-stack";
import { createLazyScreen } from "@porterchain/mobile-performance";
import type { NavigationStackParamList } from "../types";

const NavigationScreen = createLazyScreen(
  () => import("../../screens/navigation/NavigationScreen"),
  "NavigationScreen"
);

const Stack = createNativeStackNavigator<NavigationStackParamList>();

export function NavigationStack() {
  return (
    <Stack.Navigator screenOptions={{ headerShown: false, freezeOnBlur: true }}>
      <Stack.Screen name="Navigation" component={NavigationScreen as never} />
    </Stack.Navigator>
  );
}
