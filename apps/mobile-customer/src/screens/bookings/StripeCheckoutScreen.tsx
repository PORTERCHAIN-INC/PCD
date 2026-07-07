import { useEffect, useState } from "react";
import { Linking, View } from "react-native";
import { useNavigation, useRoute } from "@react-navigation/native";
import type { NativeStackNavigationProp } from "@react-navigation/native-stack";
import type { RouteProp } from "@react-navigation/native";
import * as WebBrowser from "expo-web-browser";
import { useTheme } from "@porterchain/mobile-theme";
import { Body, Button, LoadingState, Screen } from "@porterchain/mobile-ui";
import { useCustomerApi } from "../../api/CustomerApiContext";
import { ScreenHeader } from "../../components/ScreenHeader";
import type { BookingsStackParamList } from "../../navigation/types";

export function StripeCheckoutScreen() {
  const { theme } = useTheme();
  const api = useCustomerApi();
  const navigation = useNavigation<NativeStackNavigationProp<BookingsStackParamList>>();
  const route = useRoute<RouteProp<BookingsStackParamList, "StripeCheckout">>();
  const [polling, setPolling] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [checking, setChecking] = useState(false);

  async function checkPaymentStatus() {
    setChecking(true);
    setError(null);
    try {
      const status = await api.getBookingConfirmation(route.params.quoteId);
      if (status.status === "ready" && status.confirmation) {
        navigation.replace("BookingConfirmation", { quoteId: route.params.quoteId });
        return;
      }
      setError("Payment not confirmed yet. Complete checkout in the browser, then check again.");
    } catch (e) {
      setError(e instanceof Error ? e.message : "Unable to verify payment");
    } finally {
      setChecking(false);
    }
  }

  useEffect(() => {
    void (async () => {
      if (route.params.mockCheckout) {
        try {
          await api.mockCompleteCheckout(route.params.quoteId);
          navigation.replace("BookingConfirmation", { quoteId: route.params.quoteId });
        } catch (e) {
          setError(e instanceof Error ? e.message : "Mock checkout failed");
        }
        return;
      }

      if (route.params.checkoutUrl) {
        await WebBrowser.openBrowserAsync(route.params.checkoutUrl);
        setPolling(true);
      }
    })();
  }, [api, navigation, route.params]);

  useEffect(() => {
    if (!polling) return;
    const timer = setInterval(() => {
      void api.getBookingConfirmation(route.params.quoteId).then((status) => {
        if (status.status === "ready" && status.confirmation) {
          clearInterval(timer);
          navigation.replace("BookingConfirmation", { quoteId: route.params.quoteId });
        }
      });
    }, 2500);
    return () => clearInterval(timer);
  }, [api, navigation, polling, route.params.quoteId]);

  if (polling) {
    return (
      <Screen>
        <LoadingState message="Waiting for Stripe payment…" />
      </Screen>
    );
  }

  return (
    <Screen>
      <ScreenHeader title="Stripe checkout" />
      <View style={{ padding: theme.spacing.lg, gap: theme.spacing.md }}>
        {error ? <Body style={{ color: theme.colors.danger }}>{error}</Body> : null}
        <Body muted>
          Complete payment in the browser. Porterchain confirms via Stripe webhook — use Check
          payment status when done.
        </Body>
        {route.params.checkoutUrl ? (
          <Button
            label="Reopen checkout"
            fullWidth
            onPress={() => void Linking.openURL(route.params.checkoutUrl)}
          />
        ) : null}
        <Button
          label="Check payment status"
          variant="secondary"
          loading={checking}
          fullWidth
          onPress={() => void checkPaymentStatus()}
        />
      </View>
    </Screen>
  );
}
