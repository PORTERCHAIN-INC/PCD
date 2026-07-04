import { useEffect, useState } from "react";
import { Linking, ScrollView } from "react-native";
import { useRoute } from "@react-navigation/native";
import type { RouteProp } from "@react-navigation/native";
import { useTheme } from "@porterchain/mobile-theme";
import { Body, Button, Card, CardHeader, Screen, SuccessState } from "@porterchain/mobile-ui";
import { useCustomerApi } from "../../api/CustomerApiContext";
import { ScreenHeader } from "../../components/ScreenHeader";
import type { BookingsStackParamList } from "../../navigation/types";

export function BookingConfirmationScreen() {
  const { theme } = useTheme();
  const api = useCustomerApi();
  const route = useRoute<RouteProp<BookingsStackParamList, "BookingConfirmation">>();
  const [confirmation, setConfirmation] = useState<Awaited<ReturnType<typeof api.getBookingConfirmation>>["confirmation"]>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    void (async () => {
      try {
        const status = await api.getBookingConfirmation(route.params.quoteId);
        setConfirmation(status.confirmation);
      } finally {
        setLoading(false);
      }
    })();
  }, [api, route.params.quoteId]);

  if (loading) return <Screen><SuccessState title="Confirming…" message="Finalizing your booking" /></Screen>;

  if (!confirmation) {
    return (
      <Screen>
        <ScreenHeader title="Processing" />
        <Body style={{ padding: theme.spacing.lg }} muted>Payment is still processing. Pull to refresh shortly.</Body>
      </Screen>
    );
  }

  return (
    <Screen>
      <ScreenHeader title="Booking confirmed" subtitle={confirmation.booking_number} />
      <ScrollView contentContainerStyle={{ padding: theme.spacing.lg, gap: theme.spacing.lg }}>
        <Card>
          <CardHeader title="Tracking" subtitle={confirmation.tracking_number} />
          <Body>{confirmation.pickup?.formatted} → {confirmation.dropoff?.formatted}</Body>
          <Body muted style={{ marginTop: theme.spacing.sm }}>Invoice {confirmation.invoice_number}</Body>
        </Card>
        {confirmation.receipt_url ? (
          <Button label="View receipt" variant="secondary" fullWidth onPress={() => void Linking.openURL(confirmation.receipt_url!)} />
        ) : null}
      </ScrollView>
    </Screen>
  );
}
