import { useQuery } from "@tanstack/react-query";
import { ScrollView, View } from "react-native";
import { useNavigation } from "@react-navigation/native";
import type { NativeStackNavigationProp } from "@react-navigation/native-stack";
import { useTheme } from "@porterchain/mobile-theme";
import {
  Body,
  Button,
  Card,
  CardHeader,
  MetricCard,
  Screen,
  SkeletonCard,
  StatusChip,
} from "@porterchain/mobile-ui";
import { useCustomerApi } from "../../api/CustomerApiContext";
import { ScreenHeader } from "../../components/ScreenHeader";
import type { HomeStackParamList } from "../../navigation/types";

export function HomeScreen() {
  const { theme } = useTheme();
  const api = useCustomerApi();
  const navigation = useNavigation<NativeStackNavigationProp<HomeStackParamList>>();

  const { data, isLoading, error, refetch } = useQuery({
    queryKey: ["customer", "dashboard"],
    queryFn: () => api.dashboard(),
  });

  const active = data?.active_order;

  return (
    <Screen>
      <ScreenHeader title="Home" subtitle="Your deliveries at a glance" />
      <ScrollView contentContainerStyle={{ padding: theme.spacing.lg, gap: theme.spacing.lg }}>
        {isLoading ? <SkeletonCard /> : null}
        {error ? (
          <Card>
            <Body>Could not load dashboard.</Body>
            <Button
              label="Retry"
              variant="secondary"
              onPress={() => void refetch()}
              style={{ marginTop: theme.spacing.md }}
            />
          </Card>
        ) : null}

        {data ? (
          <>
            <View style={{ flexDirection: "row", gap: theme.spacing.md }}>
              <View style={{ flex: 1 }}>
                <MetricCard label="Orders" value={String(data.stats.total_orders ?? 0)} />
              </View>
              <View style={{ flex: 1 }}>
                <MetricCard label="Bookings" value={String(data.stats.total_bookings ?? 0)} />
              </View>
            </View>

            <Card>
              <CardHeader
                title={active ? "Active shipment" : "No active shipment"}
                subtitle={active?.tracking_number}
                action={active ? <StatusChip label={active.state} tone="active" /> : null}
              />
              {active ? (
                <>
                  <Body muted>
                    {active.pickup?.formatted} → {active.dropoff?.formatted}
                  </Body>
                  <Button
                    label="Track live"
                    style={{ marginTop: theme.spacing.lg }}
                    fullWidth
                    onPress={() =>
                      navigation.getParent()?.navigate("Tracking", {
                        screen: "LiveMap",
                        params: { trackingNumber: active.tracking_number },
                      })
                    }
                  />
                </>
              ) : (
                <Button
                  label="Book a delivery"
                  style={{ marginTop: theme.spacing.md }}
                  onPress={() => navigation.getParent()?.navigate("Bookings", { screen: "Quote" })}
                />
              )}
            </Card>

            <Button
              label="Get a quote"
              variant="secondary"
              fullWidth
              onPress={() => navigation.getParent()?.navigate("Bookings", { screen: "Quote" })}
            />
          </>
        ) : null}
      </ScrollView>
    </Screen>
  );
}
