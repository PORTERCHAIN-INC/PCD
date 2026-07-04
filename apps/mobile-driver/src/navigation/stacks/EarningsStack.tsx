import { createNativeStackNavigator } from "@react-navigation/native-stack";
import { EarningsScreen } from "../../screens/earnings/EarningsScreen";
import type { EarningsStackParamList } from "../types";

const Stack = createNativeStackNavigator<EarningsStackParamList>();

export function EarningsStack() {
  return (
    <Stack.Navigator screenOptions={{ headerShown: false }}>
      <Stack.Screen name="Earnings" component={EarningsScreen} />
    </Stack.Navigator>
  );
}
