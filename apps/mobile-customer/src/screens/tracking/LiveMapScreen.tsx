import { useState } from "react";
import { useForegroundAwarePolling } from "@porterchain/mobile-performance";
import { View } from "react-native";
import { useRoute } from "@react-navigation/native";
import type { RouteProp } from "@react-navigation/native";
import { useQuery } from "@tanstack/react-query";
import { useTheme } from "@porterchain/mobile-theme";
import { Body, Card, LoadingState, Screen } from "@porterchain/mobile-ui";
import { EnterpriseMap, liveTrackingToMapSession } from "@porterchain/mobile-maps";
import { useCustomerApi } from "../../api/CustomerApiContext";
import { ScreenHeader } from "../../components/ScreenHeader";
import type { TrackingStackParamList } from "../../navigation/types";

export function LiveMapScreen() {
  const { theme } = useTheme();
  const api = useCustomerApi();
  const route = useRoute<RouteProp<TrackingStackParamList, "LiveMap">>();
  const [replayIndex, setReplayIndex] = useState<number | null>(null);

  const pollMs = useForegroundAwarePolling(15000);

  const { data, isLoading } = useQuery({
    queryKey: ["customer", "live-tracking", route.params.trackingNumber],
    queryFn: () => api.getLiveTracking(route.params.trackingNumber),
    refetchInterval: pollMs,
  });

  const live = data?.live_tracking as Record<string, unknown> | null | undefined;
  const mapSession = live
    ? liveTrackingToMapSession({
        ...live,
        driver_location: live.driver_location as { lat: number; lng: number } | undefined,
        status: data?.state,
      })
    : null;

  return (
    <Screen>
      <ScreenHeader title="Live map" subtitle={route.params.trackingNumber} />
      <View style={{ flex: 1, padding: theme.spacing.lg, gap: theme.spacing.md }}>
        {isLoading ? <LoadingState message="Loading live position…" /> : null}
        {mapSession ? (
          <EnterpriseMap
            session={mapSession}
            height={360}
            showTraffic
            showGeofences
            replayIndex={replayIndex}
            onReplayIndexChange={setReplayIndex}
          />
        ) : null}
        <Card>
          <Body>Status: {data?.state ?? "—"}</Body>
          <Body muted>Tracking via Porterchain API → Fleetbase adapter</Body>
        </Card>
      </View>
    </Screen>
  );
}
