import { createNativeStackNavigator } from "@react-navigation/native-stack";
import { ShiftScreen } from "../../screens/shift/ShiftScreen";
import type { ShiftStackParamList } from "../types";

const Stack = createNativeStackNavigator<ShiftStackParamList>();

export function ShiftStack() {
  return (
    <Stack.Navigator screenOptions={{ headerShown: false }}>
      <Stack.Screen name="Shift" component={ShiftScreen} />
    </Stack.Navigator>
  );
}
