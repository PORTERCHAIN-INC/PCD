import { useQuery } from "@tanstack/react-query";
import { ScrollView, View } from "react-native";
import { useTheme } from "@porterchain/mobile-theme";
import { Body, Card, MetricCard, Screen, SkeletonCard } from "@porterchain/mobile-ui";
import { useDriverApi } from "../../api/DriverApiContext";
import { ScreenHeader } from "../../components/ScreenHeader";

function money(cents: number) {
  return new Intl.NumberFormat("en-CA", { style: "currency", currency: "CAD" }).format(cents / 100);
}

export function EarningsScreen() {
  const { theme } = useTheme();
  const api = useDriverApi();

  const { data, isLoading } = useQuery({
    queryKey: ["driver", "earnings"],
    queryFn: () => api.earningsSnapshot(),
  });

  return (
    <Screen>
      <ScreenHeader title="Earnings" subtitle="Wallet & payouts" />
      <ScrollView contentContainerStyle={{ padding: theme.spacing.lg, gap: theme.spacing.lg }}>
        {isLoading ? <SkeletonCard /> : null}
        {data ? (
          <>
            <View style={{ flexDirection: "row", gap: theme.spacing.md }}>
              <View style={{ flex: 1 }}>
                <MetricCard label="Today" value={money(data.today_cents)} />
              </View>
              <View style={{ flex: 1 }}>
                <MetricCard label="Week" value={money(data.week_cents)} />
              </View>
            </View>
            <Card>
              <Body style={{ fontWeight: "600" }}>Wallet balance</Body>
              <Body muted>{money(data.wallet_balance_cents)}</Body>
              <Body muted style={{ marginTop: theme.spacing.sm }}>
                {data.completed_deliveries_today} deliveries today
              </Body>
            </Card>
          </>
        ) : null}
      </ScrollView>
    </Screen>
  );
}
