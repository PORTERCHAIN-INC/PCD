import { useQuery } from "@tanstack/react-query";
import { View } from "react-native";
import { useNavigation } from "@react-navigation/native";
import type { NativeStackNavigationProp } from "@react-navigation/native-stack";
import { EnterpriseFlashList, LIST_ITEM_SIZES } from "@porterchain/mobile-performance";
import { useTheme } from "@porterchain/mobile-theme";
import { ListItem, Screen, SkeletonList, StatusChip } from "@porterchain/mobile-ui";
import { useCustomerApi } from "../../api/CustomerApiContext";
import { ScreenHeader } from "../../components/ScreenHeader";
import type { TrackingStackParamList } from "../../navigation/types";

export function HistoryScreen() {
  const { theme } = useTheme();
  const api = useCustomerApi();
  const navigation = useNavigation<NativeStackNavigationProp<TrackingStackParamList>>();

  const { data, isLoading } = useQuery({
    queryKey: ["customer", "orders"],
    queryFn: async () => (await api.dashboard()).orders,
  });

  return (
    <Screen>
      <ScreenHeader title="Order history" subtitle="Past deliveries" />
      {isLoading ? (
        <View style={{ padding: theme.spacing.lg }}>
          <SkeletonList />
        </View>
      ) : (
        <EnterpriseFlashList
          data={data ?? []}
          estimatedItemSize={LIST_ITEM_SIZES.standard}
          keyExtractor={(order) => order.order_id}
          contentContainerStyle={{ padding: theme.spacing.lg }}
          renderItem={({ item: order }) => (
            <ListItem
              title={order.tracking_number}
              subtitle={order.pickup?.formatted}
              meta={order.scheduled_at?.slice(0, 10)}
              trailing={<StatusChip label={order.state} tone="completed" />}
              onPress={() =>
                navigation.navigate("LiveMap", { trackingNumber: order.tracking_number })
              }
            />
          )}
        />
      )}
    </Screen>
  );
}
