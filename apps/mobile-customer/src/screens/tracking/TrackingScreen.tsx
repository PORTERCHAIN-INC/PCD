import { useState } from "react";
import { ScrollView } from "react-native";
import { useNavigation, useRoute } from "@react-navigation/native";
import type { NativeStackNavigationProp } from "@react-navigation/native-stack";
import type { RouteProp } from "@react-navigation/native";
import { useTheme } from "@porterchain/mobile-theme";
import { Body, Button, Card, CardHeader, Input, Screen, StatusChip } from "@porterchain/mobile-ui";
import { useCustomerApi } from "../../api/CustomerApiContext";
import { ScreenHeader } from "../../components/ScreenHeader";
import type { TrackingStackParamList } from "../../navigation/types";

export function TrackingScreen() {
  const { theme } = useTheme();
  const api = useCustomerApi();
  const navigation = useNavigation<NativeStackNavigationProp<TrackingStackParamList>>();
  const route = useRoute<RouteProp<TrackingStackParamList, "Tracking">>();

  const [trackingNumber, setTrackingNumber] = useState(route.params?.trackingNumber ?? "");
  const [order, setOrder] = useState<Awaited<ReturnType<typeof api.getOrder>> | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function lookup() {
    setLoading(true);
    setError(null);
    try {
      const result = await api.getOrder(trackingNumber.trim());
      setOrder(result);
    } catch (e) {
      setOrder(null);
      setError(e instanceof Error ? e.message : "Not found");
    } finally {
      setLoading(false);
    }
  }

  return (
    <Screen>
      <ScreenHeader
        title="Tracking"
        subtitle="Public order lookup"
        right={
          <Button
            label="History"
            size="sm"
            variant="ghost"
            onPress={() => navigation.navigate("History")}
          />
        }
      />
      <ScrollView contentContainerStyle={{ padding: theme.spacing.lg, gap: theme.spacing.lg }}>
        <Input
          label="Tracking number"
          value={trackingNumber}
          onChangeText={setTrackingNumber}
          autoCapitalize="characters"
          placeholder="PC-XXXXXX"
        />
        <Button label="Track shipment" loading={loading} fullWidth onPress={() => void lookup()} />
        {error ? <Body style={{ color: theme.colors.danger }}>{error}</Body> : null}

        {order ? (
          <Card>
            <CardHeader
              title={order.tracking_number}
              subtitle={order.state}
              action={<StatusChip label={order.state} tone="active" />}
            />
            <Body>
              {order.pickup?.formatted} → {order.dropoff?.formatted}
            </Body>
            <Button
              label="Live map"
              style={{ marginTop: theme.spacing.lg }}
              fullWidth
              onPress={() =>
                navigation.navigate("LiveMap", { trackingNumber: order.tracking_number })
              }
            />
          </Card>
        ) : null}
      </ScrollView>
    </Screen>
  );
}
