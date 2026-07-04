import { View } from "react-native";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useNavigation } from "@react-navigation/native";
import type { NativeStackNavigationProp } from "@react-navigation/native-stack";
import { DRIVER_OFFLINE_ACTIONS } from "@porterchain/mobile-api";
import { useOfflineSync } from "@porterchain/mobile-offline";
import { EnterpriseFlashList, LIST_ITEM_SIZES } from "@porterchain/mobile-performance";
import {
  Body,
  Button,
  ListItem,
  Screen,
  SkeletonList,
  StatusChip,
} from "@porterchain/mobile-ui";
import { useDriverApi } from "../../api/DriverApiContext";
import { ScreenHeader } from "../../components/ScreenHeader";
import type { JobsStackParamList } from "../../navigation/types";

export function AssignmentQueueScreen() {
  const api = useDriverApi();
  const { runDirectOrQueue } = useOfflineSync();
  const queryClient = useQueryClient();
  const navigation = useNavigation<NativeStackNavigationProp<JobsStackParamList>>();

  const { data, isLoading, refetch } = useQuery({
    queryKey: ["driver", "jobs", "queue"],
    queryFn: () => api.jobs(),
  });

  const queue = data?.upcoming ?? [];

  async function accept(orderId: string) {
    const result = await runDirectOrQueue(
      DRIVER_OFFLINE_ACTIONS.ACCEPT_ORDER,
      { order_id: orderId },
      () => api.acceptOrder(orderId)
    );
    if (result.mode === "online") {
      await queryClient.invalidateQueries({ queryKey: ["driver", "jobs"] });
    }
  }

  async function reject(orderId: string) {
    const result = await runDirectOrQueue(
      DRIVER_OFFLINE_ACTIONS.REJECT_ORDER,
      { order_id: orderId, reason: "driver_declined" },
      () => api.rejectOrder(orderId, "driver_declined")
    );
    if (result.mode === "online") {
      await queryClient.invalidateQueries({ queryKey: ["driver", "jobs"] });
    }
  }

  return (
    <Screen>
      <ScreenHeader title="Assignment queue" subtitle="Accept or reject offers" />
      {isLoading ? (
        <View style={{ padding: 16 }}>
          <SkeletonList />
        </View>
      ) : (
        <EnterpriseFlashList
          data={queue}
          estimatedItemSize={LIST_ITEM_SIZES.jobQueue}
          keyExtractor={(job) => job.order_id}
          contentContainerStyle={{ padding: 16 }}
          ListEmptyComponent={<Body muted>No assignments in queue.</Body>}
          ListFooterComponent={<Button label="Refresh" variant="ghost" onPress={() => void refetch()} />}
          renderItem={({ item: job }) => (
            <View style={{ gap: 8, marginBottom: 12 }}>
              <ListItem
                title={job.tracking_number}
                subtitle={`${job.pickup_address} → ${job.delivery_address}`}
                trailing={<StatusChip label="Offer" tone="warning" />}
                onPress={() => navigation.navigate("JobDetail", { orderId: job.order_id })}
                showDivider={false}
              />
              <View style={{ flexDirection: "row", gap: 8 }}>
                <Button label="Accept" size="sm" style={{ flex: 1 }} onPress={() => void accept(job.order_id)} />
                <Button label="Reject" size="sm" variant="outline" style={{ flex: 1 }} onPress={() => void reject(job.order_id)} />
              </View>
            </View>
          )}
        />
      )}
    </Screen>
  );
}
