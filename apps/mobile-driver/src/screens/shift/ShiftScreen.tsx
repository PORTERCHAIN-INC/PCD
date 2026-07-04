import { useQuery, useQueryClient } from "@tanstack/react-query";
import { ScrollView } from "react-native";
import { useOfflineSync } from "@porterchain/mobile-offline";
import { useTheme } from "@porterchain/mobile-theme";
import { Body, Button, Card, CardHeader, Screen, StatusChip } from "@porterchain/mobile-ui";
import { useDriverApi } from "../../api/DriverApiContext";
import { ScreenHeader } from "../../components/ScreenHeader";
import { startGpsTracking, stopGpsTracking } from "../../services/location";

export function ShiftScreen() {
  const { theme } = useTheme();
  const api = useDriverApi();
  const { enqueueGps } = useOfflineSync();
  const queryClient = useQueryClient();

  const { data, refetch } = useQuery({
    queryKey: ["driver", "shift"],
    queryFn: () => api.shift(),
  });

  async function mutate(fn: () => Promise<unknown>) {
    await fn();
    await queryClient.invalidateQueries({ queryKey: ["driver", "shift"] });
    await queryClient.invalidateQueries({ queryKey: ["driver", "dashboard"] });
  }

  return (
    <Screen>
      <ScreenHeader title="Shift" subtitle={data?.working_hours_label ?? "—"} />
      <ScrollView contentContainerStyle={{ padding: theme.spacing.lg, gap: theme.spacing.lg }}>
        <Card>
          <CardHeader
            title={data?.shift_active ? "On shift" : "Off shift"}
            subtitle={data?.availability}
            action={<StatusChip label={data?.is_online ? "Online" : "Offline"} tone={data?.is_online ? "active" : "neutral"} />}
          />
          <Body muted>{data?.mileage_km ?? 0} km · Route {data?.current_route?.route_id ?? "—"}</Body>
        </Card>

        <Button label="Go online" fullWidth onPress={() => void mutate(() => api.setAvailability("online"))} />
        <Button label="Start shift" variant="secondary" fullWidth onPress={() => {
          void mutate(async () => {
            await api.shiftStart(data?.current_route?.route_id);
            await startGpsTracking(api, { onOfflinePing: enqueueGps });
          });
        }} />
        <Button label="Take break" variant="secondary" fullWidth onPress={() => void mutate(() => api.shiftBreak())} />
        <Button label="Resume" variant="secondary" fullWidth onPress={() => void mutate(() => api.shiftResume())} />
        <Button label="End shift" variant="outline" fullWidth onPress={() => {
          void mutate(async () => {
            stopGpsTracking();
            await api.shiftEnd();
            await api.setAvailability("offline");
          });
        }} />
        <Button label="Refresh" variant="ghost" onPress={() => void refetch()} />
      </ScrollView>
    </Screen>
  );
}
