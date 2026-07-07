import { createNativeStackNavigator } from "@react-navigation/native-stack";
import { createLazyScreen } from "@porterchain/mobile-performance";
import { BookingsScreen } from "../../screens/bookings/BookingsScreen";
import { QuoteScreen } from "../../screens/bookings/QuoteScreen";
import { BookingScreen } from "../../screens/bookings/BookingScreen";
import { BookingDraftScreen } from "../../screens/bookings/BookingDraftScreen";
import { BookingConfirmationScreen } from "../../screens/bookings/BookingConfirmationScreen";
import type { BookingsStackParamList } from "../types";

const StripeCheckoutScreen = createLazyScreen(
  () => import("../../screens/bookings/StripeCheckoutScreen"),
  "StripeCheckoutScreen"
);

const Stack = createNativeStackNavigator<BookingsStackParamList>();

export function BookingsStack() {
  return (
    <Stack.Navigator screenOptions={{ headerShown: false, freezeOnBlur: true }}>
      <Stack.Screen name="Bookings" component={BookingsScreen} />
      <Stack.Screen name="Quote" component={QuoteScreen} />
      <Stack.Screen name="Booking" component={BookingScreen} />
      <Stack.Screen name="BookingDraft" component={BookingDraftScreen} />
      <Stack.Screen name="StripeCheckout" component={StripeCheckoutScreen as never} />
      <Stack.Screen name="BookingConfirmation" component={BookingConfirmationScreen} />
    </Stack.Navigator>
  );
}
