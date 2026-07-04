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

export function InvoicesScreen() {
  const { theme } = useTheme();
  const api = useCustomerApi();

  const { data, isLoading } = useQuery({
    queryKey: ["customer", "invoices"],
    queryFn: async () => (await api.dashboard()).invoices,
  });

  return (
    <Screen>
      <ScreenHeader title="Invoices" subtitle="From your dashboard" />
      {isLoading ? (
        <View style={{ padding: theme.spacing.lg }}>
          <SkeletonList />
        </View>
      ) : (
        <EnterpriseFlashList
          data={data ?? []}
          estimatedItemSize={LIST_ITEM_SIZES.standard}
          keyExtractor={(invoice) => invoice.invoice_id}
          contentContainerStyle={{ padding: theme.spacing.lg }}
          ListEmptyComponent={<Body muted style={{ padding: theme.spacing.lg }}>No invoices yet.</Body>}
          renderItem={({ item: invoice }) => (
            <ListItem
              title={invoice.invoice_number}
              subtitle={formatMoney(invoice.amount_cents, invoice.currency)}
              meta={invoice.created_at?.slice(0, 10)}
              trailing={
                invoice.pdf_url ? (
                  <Button label="PDF" size="sm" variant="ghost" onPress={() => void Linking.openURL(invoice.pdf_url!)} />
                ) : undefined
              }
            />
          )}
        />
      )}
    </Screen>
  );
}
