import { useQuery } from "@tanstack/react-query";
import { View } from "react-native";
import { useNavigation } from "@react-navigation/native";
import type { NativeStackNavigationProp } from "@react-navigation/native-stack";
import { EnterpriseFlashList, LIST_ITEM_SIZES } from "@porterchain/mobile-performance";
import { useTheme } from "@porterchain/mobile-theme";
import {
  Body,
  Button,
  Card,
  CardHeader,
  ListItem,
  Screen,
  SkeletonList,
  StatusChip,
} from "@porterchain/mobile-ui";
import { useCustomerApi } from "../../api/CustomerApiContext";
import { ScreenHeader } from "../../components/ScreenHeader";
import type { BookingsStackParamList } from "../../navigation/types";

export function BookingsScreen() {
  const { theme } = useTheme();
  const api = useCustomerApi();
  const navigation = useNavigation<NativeStackNavigationProp<BookingsStackParamList>>();

  const { data, isLoading, refetch } = useQuery({
    queryKey: ["customer", "dashboard", "bookings"],
    queryFn: () => api.dashboard(),
  });

  const bookings = data?.bookings ?? [];

  return (
    <Screen>
      <ScreenHeader
        title="Bookings"
        subtitle="Quotes, drafts, and checkout"
        right={<Button label="New quote" size="sm" onPress={() => navigation.navigate("Quote")} />}
      />
      {isLoading ? (
        <View style={{ padding: theme.spacing.lg }}>
          <SkeletonList />
        </View>
      ) : (
        <EnterpriseFlashList
          data={bookings}
          estimatedItemSize={LIST_ITEM_SIZES.standard}
          keyExtractor={(booking) => booking.booking_id}
          contentContainerStyle={{ padding: theme.spacing.lg }}
          ListHeaderComponent={
            <View style={{ gap: theme.spacing.lg, marginBottom: theme.spacing.md }}>
              <Button
                label="Resume booking draft"
                variant="secondary"
                fullWidth
                onPress={() => navigation.navigate("BookingDraft")}
              />
              <Body style={{ fontWeight: "700" }}>Recent bookings</Body>
            </View>
          }
          ListEmptyComponent={
            <Card padded>
              <Body muted>No bookings yet. Start with a quote.</Body>
            </Card>
          }
          ListFooterComponent={
            <View style={{ gap: theme.spacing.lg, marginTop: theme.spacing.lg }}>
              <Card onPress={() => navigation.navigate("Quote")}>
                <CardHeader title="Quick quote" subtitle="Same-day delivery across your city" />
                <Body muted>Enter pickup and dropoff to see instant pricing.</Body>
              </Card>
              <Button label="Refresh" variant="ghost" onPress={() => void refetch()} />
            </View>
          }
          renderItem={({ item: booking }) => (
            <ListItem
              title={booking.booking_number}
              subtitle={booking.state}
              trailing={
                <StatusChip
                  label={booking.state}
                  tone={booking.state === "completed" ? "completed" : "pending"}
                />
              }
              onPress={() => {
                if (booking.quote_id)
                  navigation.navigate("BookingConfirmation", { quoteId: booking.quote_id });
              }}
            />
          )}
        />
      )}
    </Screen>
  );
}
