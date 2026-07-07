import { useEffect, useState } from "react";
import { ScrollView } from "react-native";
import { useNavigation, useRoute } from "@react-navigation/native";
import type { NativeStackNavigationProp } from "@react-navigation/native-stack";
import type { RouteProp } from "@react-navigation/native";
import { useTheme } from "@porterchain/mobile-theme";
import { Body, Button, Card, CardHeader, Input, Screen } from "@porterchain/mobile-ui";
import { useCustomerApi } from "../../api/CustomerApiContext";
import { ScreenHeader } from "../../components/ScreenHeader";
import { useAuthStore } from "../../store/auth-store";
import { useSettingsStore } from "../../store/settings-store";
import type { BookingsStackParamList } from "../../navigation/types";

export function BookingScreen() {
  const { theme } = useTheme();
  const api = useCustomerApi();
  const navigation = useNavigation<NativeStackNavigationProp<BookingsStackParamList>>();
  const route = useRoute<RouteProp<BookingsStackParamList, "Booking">>();
  const clerkUserId = useAuthStore((s) => s.clerkUserId) ?? "dev_clerk_user";
  const email = useAuthStore((s) => s.email) ?? "customer@porterchain.com";
  const ensureVisitorSession = useSettingsStore((s) => s.ensureVisitorSession);

  const [phone, setPhone] = useState("");
  const [quote, setQuote] = useState<Awaited<ReturnType<typeof api.getQuote>> | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    void api
      .getQuote(route.params.quoteId)
      .then(setQuote)
      .catch(() => setError("Quote not found"));
  }, [api, route.params.quoteId]);

  async function onBook() {
    setLoading(true);
    setError(null);
    try {
      const result = await api.startBooking({
        quote_id: route.params.quoteId,
        email,
        phone,
        clerk_user_id: clerkUserId,
        anonymous_session_id: ensureVisitorSession(),
        terms_accepted: true,
        privacy_accepted: true,
      });

      if (result.checkout_url) {
        navigation.navigate("StripeCheckout", {
          checkoutUrl: result.checkout_url,
          quoteId: route.params.quoteId,
          mockCheckout: result.mock_checkout,
        });
      } else if (result.mock_checkout) {
        navigation.navigate("StripeCheckout", {
          checkoutUrl: "",
          quoteId: route.params.quoteId,
          mockCheckout: true,
        });
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : "Booking failed");
    } finally {
      setLoading(false);
    }
  }

  return (
    <Screen>
      <ScreenHeader title="Confirm booking" subtitle={quote?.amount_display} />
      <ScrollView contentContainerStyle={{ padding: theme.spacing.lg, gap: theme.spacing.lg }}>
        {quote ? (
          <Card>
            <CardHeader
              title="Route"
              subtitle={`${quote.pickup?.formatted ?? ""} → ${quote.dropoff?.formatted ?? ""}`}
            />
            <Body muted>Vehicle: {quote.vehicle_class}</Body>
          </Card>
        ) : null}

        <Input
          label="Phone"
          value={phone}
          onChangeText={setPhone}
          keyboardType="phone-pad"
          placeholder="+1 416 555 0100"
        />
        <Input label="Email" value={email} editable={false} />
        {error ? <Body style={{ color: theme.colors.danger }}>{error}</Body> : null}
        <Button
          label="Continue to payment"
          loading={loading}
          fullWidth
          onPress={() => void onBook()}
        />
      </ScrollView>
    </Screen>
  );
}
