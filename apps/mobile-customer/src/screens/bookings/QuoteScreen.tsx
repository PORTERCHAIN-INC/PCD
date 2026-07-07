import { useState } from "react";
import { ScrollView } from "react-native";
import { useNavigation, useRoute } from "@react-navigation/native";
import type { NativeStackNavigationProp } from "@react-navigation/native-stack";
import type { RouteProp } from "@react-navigation/native";
import { useTheme } from "@porterchain/mobile-theme";
import { Body, Button, Input, Screen, Title } from "@porterchain/mobile-ui";
import { useCustomerApi } from "../../api/CustomerApiContext";
import { ScreenHeader } from "../../components/ScreenHeader";
import { useSettingsStore } from "../../store/settings-store";
import type { BookingsStackParamList } from "../../navigation/types";

export function QuoteScreen() {
  const { theme } = useTheme();
  const api = useCustomerApi();
  const navigation = useNavigation<NativeStackNavigationProp<BookingsStackParamList>>();
  const route = useRoute<RouteProp<BookingsStackParamList, "Quote">>();
  const ensureVisitorSession = useSettingsStore((s) => s.ensureVisitorSession);

  const [pickup, setPickup] = useState("");
  const [dropoff, setDropoff] = useState("");
  const [vehicleClass, setVehicleClass] = useState("car");
  const [packageType, setPackageType] = useState("parcel");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function onSubmit() {
    setLoading(true);
    setError(null);
    try {
      if (route.params?.rebookOrderId) {
        const rebook = await api.rebook(route.params.rebookOrderId);
        setPickup(rebook.pickup.formatted);
        setDropoff(rebook.dropoff.formatted);
      }

      const quote = await api.createQuote({
        visitor_session_id: ensureVisitorSession(),
        pickup: { formatted: pickup },
        dropoff: { formatted: dropoff },
        vehicle_class: vehicleClass,
        package_type: packageType,
        scheduled_at: new Date().toISOString(),
        schedule_mode: "now",
      });
      navigation.navigate("Booking", { quoteId: quote.quote_id });
    } catch (e) {
      setError(e instanceof Error ? e.message : "Quote failed");
    } finally {
      setLoading(false);
    }
  }

  return (
    <Screen>
      <ScreenHeader title="Get a quote" subtitle="Instant pricing" />
      <ScrollView contentContainerStyle={{ padding: theme.spacing.lg, gap: theme.spacing.md }}>
        <Input
          label="Pickup address"
          value={pickup}
          onChangeText={setPickup}
          placeholder="123 King St W, Toronto"
        />
        <Input
          label="Dropoff address"
          value={dropoff}
          onChangeText={setDropoff}
          placeholder="456 Bay St, Toronto"
        />
        <Input
          label="Vehicle"
          value={vehicleClass}
          onChangeText={setVehicleClass}
          placeholder="car | van | bike"
        />
        <Input
          label="Package type"
          value={packageType}
          onChangeText={setPackageType}
          placeholder="parcel"
        />
        {error ? <Body style={{ color: theme.colors.danger }}>{error}</Body> : null}
        <Button label="See price" loading={loading} fullWidth onPress={() => void onSubmit()} />
        <Title style={{ marginTop: theme.spacing.md }}>Saved draft</Title>
        <Body muted>Your in-progress booking is auto-saved while you quote and checkout.</Body>
      </ScrollView>
    </Screen>
  );
}
