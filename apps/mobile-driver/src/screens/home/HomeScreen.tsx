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
import { useDriverApi } from "../../api/DriverApiContext";
import { ScreenHeader } from "../../components/ScreenHeader";
import type { HomeStackParamList } from "../../navigation/types";

function formatMoney(cents: number) {
  return new Intl.NumberFormat("en-CA", { style: "currency", currency: "CAD" }).format(cents / 100);
}

export function HomeScreen() {
  const { theme } = useTheme();
  const api = useDriverApi();
  const navigation = useNavigation<NativeStackNavigationProp<HomeStackParamList>>();

  const { data, isLoading, refetch } = useQuery({
    queryKey: ["driver", "dashboard"],
    queryFn: () => api.dashboard(),
  });

  const tabNav = navigation.getParent();

  return (
    <Screen>
      <ScreenHeader title="Dashboard" subtitle="Today's deliveries" />
      <ScrollView contentContainerStyle={{ padding: theme.spacing.lg, gap: theme.spacing.lg }}>
        {isLoading ? <SkeletonCard /> : null}
        {data ? (
          <>
            <View style={{ flexDirection: "row", gap: theme.spacing.md }}>
              <View style={{ flex: 1 }}>
                <MetricCard label="Today" value={formatMoney(data.todays_earnings_cents)} />
              </View>
              <View style={{ flex: 1 }}>
                <MetricCard
                  label="Stops"
                  value={`${data.todays_stops_completed}/${data.todays_stops_total}`}
                />
              </View>
            </View>
            <Card>
              <CardHeader
                title="Shift status"
                subtitle={data.is_online ? "Online" : "Offline"}
                action={
                  <StatusChip
                    label={data.availability}
                    tone={data.is_online ? "active" : "neutral"}
                  />
                }
              />
              <Body muted>
                Performance {data.performance_score}% · Rating {data.rating ?? "—"}
              </Body>
              <Button
                label="Open shift"
                style={{ marginTop: theme.spacing.lg }}
                fullWidth
                onPress={() => tabNav?.navigate("Shift")}
              />
            </Card>
            <Button
              label="Assignment queue"
              variant="secondary"
              fullWidth
              onPress={() => tabNav?.navigate("Jobs", { screen: "AssignmentQueue" })}
            />
            <Button
              label="Start navigation"
              fullWidth
              onPress={() => tabNav?.navigate("Navigation")}
            />
          </>
        ) : null}
        <Button label="Refresh" variant="ghost" onPress={() => void refetch()} />
      </ScrollView>
    </Screen>
  );
}
