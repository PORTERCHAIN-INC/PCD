import { useMemo } from "react";
import { useQuery } from "@tanstack/react-query";
import { View } from "react-native";
import { useNavigation } from "@react-navigation/native";
import type { NativeStackNavigationProp } from "@react-navigation/native-stack";
import {
  EnterpriseFlashList,
  LIST_ITEM_SIZES,
  usePrefetchOnFocus,
} from "@porterchain/mobile-performance";
import { useTheme } from "@porterchain/mobile-theme";
import {
  Body,
  Button,
  Card,
  ListItem,
  Screen,
  SkeletonList,
  StatusChip,
} from "@porterchain/mobile-ui";
import { useDriverApi } from "../../api/DriverApiContext";
import { ScreenHeader } from "../../components/ScreenHeader";
import type { JobsStackParamList } from "../../navigation/types";
import type { DriverJobSummary } from "@porterchain/mobile-api";

type JobRow =
  | { kind: "section"; id: string; title: string }
  | { kind: "job"; id: string; job: DriverJobSummary; tone: "active" | "pending" | "completed" };

export function JobsScreen() {
  const { theme } = useTheme();
  const api = useDriverApi();
  const navigation = useNavigation<NativeStackNavigationProp<JobsStackParamList>>();

  const { data, isLoading, refetch } = useQuery({
    queryKey: ["driver", "jobs"],
    queryFn: () => api.jobs(),
  });

  usePrefetchOnFocus(["driver", "jobs", "queue"], () => api.jobs());

  const rows = useMemo((): JobRow[] => {
    const next: JobRow[] = [];
    if (data?.current) {
      next.push({ kind: "section", id: "current", title: "Current" });
      next.push({ kind: "job", id: data.current.order_id, job: data.current, tone: "active" });
    }
    if ((data?.upcoming ?? []).length > 0) {
      next.push({ kind: "section", id: "upcoming", title: "Upcoming" });
      for (const job of data!.upcoming) {
        next.push({ kind: "job", id: job.order_id, job, tone: "pending" });
      }
    }
    if ((data?.completed ?? []).length > 0) {
      next.push({ kind: "section", id: "completed", title: "Completed" });
      for (const job of data!.completed.slice(0, 20)) {
        next.push({ kind: "job", id: job.order_id, job, tone: "completed" });
      }
    }
    return next;
  }, [data]);

  return (
    <Screen>
      <ScreenHeader
        title="Jobs"
        subtitle="Today's deliveries"
        right={
          <Button
            label="Queue"
            size="sm"
            variant="ghost"
            onPress={() => navigation.navigate("AssignmentQueue")}
          />
        }
      />
      {isLoading ? (
        <View style={{ padding: theme.spacing.lg }}>
          <SkeletonList />
        </View>
      ) : (
        <EnterpriseFlashList
          data={rows}
          estimatedItemSize={LIST_ITEM_SIZES.standard}
          keyExtractor={(row) => row.id}
          contentContainerStyle={{ padding: theme.spacing.lg }}
          ListFooterComponent={
            <Button
              label="Refresh"
              variant="ghost"
              onPress={() => void refetch()}
              style={{ marginTop: theme.spacing.lg }}
            />
          }
          renderItem={({ item }) => {
            if (item.kind === "section") {
              return (
                <Body
                  style={{
                    fontWeight: "700",
                    marginTop: theme.spacing.md,
                    marginBottom: theme.spacing.sm,
                  }}
                >
                  {item.title}
                </Body>
              );
            }
            const chipTone =
              item.tone === "active" ? "active" : item.tone === "pending" ? "pending" : "completed";
            return (
              <Card style={{ marginBottom: theme.spacing.sm }}>
                <ListItem
                  title={item.job.tracking_number}
                  subtitle={
                    item.tone === "completed"
                      ? item.job.state
                      : `${item.job.pickup_address ?? ""} → ${item.job.delivery_address ?? ""}`
                  }
                  trailing={<StatusChip label={item.job.state} tone={chipTone} />}
                  onPress={() => navigation.navigate("JobDetail", { orderId: item.job.order_id })}
                  showDivider={false}
                />
              </Card>
            );
          }}
        />
      )}
    </Screen>
  );
}
