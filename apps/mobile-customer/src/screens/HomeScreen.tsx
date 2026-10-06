import { useCallback, useEffect, useState } from "react";
import { ScrollView, Text, Pressable, View, StyleSheet } from "react-native";
import { colors, typography } from "@porterchain/mobile-theme";
import { fetchDashboard, formatCad, rebook, type CustomerDashboard } from "../api";
import { humanCustomerError } from "../errors";
import { EmptyState } from "../ui/Motion";
import { PrimaryButton } from "../ui/PrimaryButton";
import { Screen } from "../ui/Screen";

type Props = {
  onBook: (rebookOrderId?: string) => void;
  onTrack: (tracking: string) => void;
};

let cachedDashboard: CustomerDashboard | null = null;

/** Last successful Home payload — used to skip the cold-start spinner on re-entry. */
export function peekCachedDashboard(): CustomerDashboard | null {
  return cachedDashboard;
}

export function HomeScreen({ onBook, onTrack }: Props) {
  const [data, setData] = useState<CustomerDashboard | null>(cachedDashboard);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(cachedDashboard == null);

  const load = useCallback(() => {
    void fetchDashboard()
      .then((dashboard) => {
        cachedDashboard = dashboard;
        setData(dashboard);
        setError(null);
      })
      .catch((err: unknown) => {
        setError(humanCustomerError(err instanceof Error ? err.message : "request_failed"));
      })
      .finally(() => setLoading(false));
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  const active = data?.active_order;

  return (
    <Screen>
      <ScrollView contentContainerStyle={styles.scroll}>
        <Text style={styles.kicker}>Porterchain</Text>
        <Text style={styles.title}>Capacity when you need it.</Text>
        <Text style={styles.lede}>
          Quote, book, and track in one place. Prices come from Porterchain.
        </Text>
        {error ? <Text style={styles.error}>{error}</Text> : null}
        <PrimaryButton label="Get a quote and book" onPress={() => onBook()} />
        {active ? (
          <Pressable onPress={() => onTrack(active.tracking_number)} style={styles.card}>
            <Text style={styles.cardLabel}>Active shipment</Text>
            <Text style={styles.cardTitle}>{active.tracking_number}</Text>
            <Text style={styles.lede}>
              {active.goods_summary ? `${active.goods_summary} · ` : ""}
              {active.state}
            </Text>
          </Pressable>
        ) : null}
        <Text style={styles.section}>Recent shipments</Text>
        {(data?.orders ?? []).length === 0 && !loading ? (
          <EmptyState
            animation="shipment"
            title="No shipments yet"
            body="Book your first delivery. Tracking and invoices show up here."
          />
        ) : null}
        {(data?.orders ?? []).slice(0, 4).map((order) => (
          <View key={order.order_id} style={styles.row}>
            <Pressable onPress={() => onTrack(order.tracking_number)}>
              <Text style={styles.rowTitle}>{order.tracking_number}</Text>
              <Text style={styles.lede}>
                {order.goods_summary ? `${order.goods_summary} · ` : ""}
                {order.state}
                {order.amount_cents != null
                  ? ` · ${formatCad(order.amount_cents, order.currency)}`
                  : ""}
              </Text>
            </Pressable>
            <Pressable
              onPress={() => {
                onBook(order.order_id);
                void rebook(order.order_id).catch(() =>
                  setError("Could not start rebook from this order.")
                );
              }}
            >
              <Text style={styles.link}>Rebook</Text>
            </Pressable>
          </View>
        ))}
        {(data?.invoices ?? []).slice(0, 2).map((invoice) => (
          <Text key={invoice.invoice_id} style={styles.lede}>
            {invoice.invoice_number} · {formatCad(invoice.amount_cents, invoice.currency)}
          </Text>
        ))}
      </ScrollView>
    </Screen>
  );
}

const styles = StyleSheet.create({
  scroll: { gap: 12, paddingBottom: 24 },
  kicker: {
    ...typography.caption,
    color: colors.secondary,
    fontWeight: "700",
    letterSpacing: 1.2,
    textTransform: "uppercase",
  },
  title: { ...typography.title, fontSize: 30, color: colors.primary },
  lede: { ...typography.body, color: colors.muted },
  section: {
    ...typography.caption,
    color: colors.muted,
    textTransform: "uppercase",
    letterSpacing: 1,
  },
  card: { backgroundColor: colors.primary, borderRadius: 16, padding: 16, gap: 4 },
  cardLabel: { ...typography.caption, color: "#ffffffcc" },
  cardTitle: { ...typography.body, color: colors.white, fontWeight: "700" },
  rowTitle: { ...typography.body, color: colors.primary, fontWeight: "700" },
  row: { backgroundColor: colors.white, borderRadius: 12, padding: 12, gap: 4 },
  link: { ...typography.caption, color: colors.secondary, fontWeight: "700" },
  error: { ...typography.caption, color: colors.danger },
});
