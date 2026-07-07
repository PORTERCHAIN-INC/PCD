import { useQuery } from "@tanstack/react-query";
import { ScrollView, View } from "react-native";
import { useNavigation, useRoute } from "@react-navigation/native";
import type { NativeStackNavigationProp } from "@react-navigation/native-stack";
import type { RouteProp } from "@react-navigation/native";
import { useTheme } from "@porterchain/mobile-theme";
import {
  Body,
  Button,
  Card,
  CardHeader,
  Screen,
  SkeletonCard,
  StatusChip,
  Timeline,
} from "@porterchain/mobile-ui";
import { useDriverApi } from "../../api/DriverApiContext";
import { ScreenHeader } from "../../components/ScreenHeader";
import type { JobsStackParamList } from "../../navigation/types";

export function JobDetailScreen() {
  const { theme } = useTheme();
  const api = useDriverApi();
  const navigation = useNavigation<NativeStackNavigationProp<JobsStackParamList>>();
  const route = useRoute<RouteProp<JobsStackParamList, "JobDetail">>();

  const { data, isLoading } = useQuery({
    queryKey: ["driver", "job", route.params.orderId],
    queryFn: () => api.job(route.params.orderId),
  });

  const routeId = data?.route_id;
  const pickupStopId = data?.pickup_stop_id;
  const deliveryStopId = data?.delivery_stop_id;

  return (
    <Screen>
      <ScreenHeader title={data?.tracking_number ?? "Job"} subtitle={data?.state} />
      <ScrollView contentContainerStyle={{ padding: theme.spacing.lg, gap: theme.spacing.lg }}>
        {isLoading ? <SkeletonCard /> : null}
        {data ? (
          <>
            <Card>
              <CardHeader
                title="Route"
                subtitle={`${data.pickup_address} → ${data.delivery_address}`}
                action={<StatusChip label={data.state} tone="active" />}
              />
              {data.special_instructions ? <Body muted>{data.special_instructions}</Body> : null}
            </Card>

            <Timeline
              items={data.timeline.map((t, i) => ({
                id: String(i),
                title: t.label,
                timestamp: t.occurred_at ?? undefined,
                tone: t.to_state?.includes("DELIVER") ? "completed" : "pending",
              }))}
            />

            <View style={{ gap: theme.spacing.sm }}>
              <Button
                label="Pickup"
                variant="secondary"
                fullWidth
                onPress={() =>
                  routeId && pickupStopId && void api.arriveStop(routeId, pickupStopId)
                }
              />
              <Button
                label="In transit"
                variant="secondary"
                fullWidth
                onPress={() =>
                  navigation.getParent()?.navigate("Navigation", {
                    screen: "Navigation",
                    params: { orderId: data.order_id },
                  })
                }
              />
              <Button
                label="Delivered / POD"
                fullWidth
                onPress={() => {
                  if (routeId && deliveryStopId)
                    navigation.navigate("Pod", {
                      orderId: data.order_id,
                      routeId,
                      stopId: deliveryStopId,
                    });
                }}
              />
              <Button
                label="Mark delivered"
                variant="outline"
                fullWidth
                onPress={() =>
                  routeId && deliveryStopId && void api.deliverStop(routeId, deliveryStopId)
                }
              />
              <Button
                label="Report incident"
                variant="outline"
                fullWidth
                onPress={() => navigation.navigate("Incident", { orderId: data.order_id })}
              />
            </View>
          </>
        ) : null}
      </ScrollView>
    </Screen>
  );
}
