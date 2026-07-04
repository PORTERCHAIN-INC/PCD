import { useState } from "react";
import { Linking, ScrollView, View } from "react-native";
import { useRoute } from "@react-navigation/native";
import type { RouteProp } from "@react-navigation/native";
import { useQuery } from "@tanstack/react-query";
import { useForegroundAwarePolling } from "@porterchain/mobile-performance";
import { useTheme } from "@porterchain/mobile-theme";
import { Body, Button, Card, Screen } from "@porterchain/mobile-ui";
import {
  EnterpriseMap,
  driverSessionToMapSession,
  formatEta,
} from "@porterchain/mobile-maps";
import { useDriverApi } from "../../api/DriverApiContext";
import { ScreenHeader } from "../../components/ScreenHeader";
import type { NavigationStackParamList } from "../../navigation/types";

export function NavigationScreen() {
  const { theme } = useTheme();
  const api = useDriverApi();
  const route = useRoute<RouteProp<NavigationStackParamList, "Navigation">>();
  const orderId = route.params?.orderId;
  const [replayIndex, setReplayIndex] = useState<number | null>(null);

  const pollMs = useForegroundAwarePolling(20000);

  const { data, refetch } = useQuery({
    queryKey: ["driver", "navigation", orderId ?? "idle"],
    queryFn: () => api.navigationSession(orderId),
    refetchInterval: pollMs,
  });

  const mapSession = data ? driverSessionToMapSession(data) : null;

  return (
    <Screen>
      <ScreenHeader title="Navigation" subtitle={data?.tracking_number ?? "Fleetbase GPS via API"} />
      <ScrollView contentContainerStyle={{ padding: theme.spacing.lg, gap: theme.spacing.lg }}>
        {mapSession ? (
          <EnterpriseMap
            session={mapSession}
            height={360}
            showTraffic
            showGeofences
            showReplayControls
            replayIndex={replayIndex}
            onReplayIndexChange={setReplayIndex}
          />
        ) : null}
        <Card>
          <Body>State: {data?.state ?? "—"}</Body>
          <Body muted>
            ETA: {formatEta(data?.eta?.duration_seconds)} · GPS: {data?.gps_source ?? "fleetbase"}
          </Body>
          <Body muted>
            Engines: {data?.routing_engines?.gps} / {data?.routing_engines?.eta} / {data?.routing_engines?.optimized_route}
          </Body>
        </Card>
        {data?.navigation_url ? (
          <Button label="Open in Google Maps" fullWidth onPress={() => void Linking.openURL(data.navigation_url!)} />
        ) : null}
        <Button label="Refresh route" variant="secondary" fullWidth onPress={() => void refetch()} />
      </ScrollView>
    </Screen>
  );
}
