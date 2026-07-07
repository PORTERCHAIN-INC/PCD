import { Linking, View } from "react-native";
import { useQuery } from "@tanstack/react-query";
import { EnterpriseFlashList, LIST_ITEM_SIZES } from "@porterchain/mobile-performance";
import { useTheme } from "@porterchain/mobile-theme";
import { Body, Button, ListItem, Screen, SkeletonList } from "@porterchain/mobile-ui";
import { useCustomerApi } from "../../api/CustomerApiContext";
import { ScreenHeader } from "../../components/ScreenHeader";

function formatMoney(cents: number, currency: string) {
  return new Intl.NumberFormat("en-CA", { style: "currency", currency }).format(cents / 100);
}

export function ReceiptsScreen() {
  const { theme } = useTheme();
  const api = useCustomerApi();

  const { data, isLoading } = useQuery({
    queryKey: ["customer", "receipts"],
    queryFn: async () => {
      const dashboard = await api.dashboard();
      return [
        ...dashboard.payments.filter((p) => p.receipt_url),
        ...dashboard.invoices
          .filter((i) => i.stripe_receipt_url)
          .map((i) => ({
            payment_id: i.invoice_id,
            status: "paid",
            amount_cents: i.amount_cents,
            currency: i.currency,
            failure_reason: null,
            receipt_url: i.stripe_receipt_url,
            retry_count: 0,
            quote_id: "",
            order_id: i.order_id,
          })),
      ];
    },
  });

  return (
    <Screen>
      <ScreenHeader title="Receipts" subtitle="Stripe payment receipts" />
      {isLoading ? (
        <View style={{ padding: theme.spacing.lg }}>
          <SkeletonList />
        </View>
      ) : (
        <EnterpriseFlashList
          data={data ?? []}
          estimatedItemSize={LIST_ITEM_SIZES.standard}
          keyExtractor={(payment) => payment.payment_id}
          contentContainerStyle={{ padding: theme.spacing.lg }}
          ListEmptyComponent={
            <Body muted style={{ padding: theme.spacing.lg }}>
              No receipts yet.
            </Body>
          }
          renderItem={({ item: payment }) => (
            <ListItem
              title={formatMoney(payment.amount_cents, payment.currency)}
              subtitle={payment.status}
              trailing={
                payment.receipt_url ? (
                  <Button
                    label="Open"
                    size="sm"
                    onPress={() => void Linking.openURL(payment.receipt_url!)}
                  />
                ) : undefined
              }
            />
          )}
        />
      )}
    </Screen>
  );
}
