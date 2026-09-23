import { useCallback, useEffect, useState } from "react";
import { Linking, Pressable, ScrollView, Text, StyleSheet } from "react-native";
import * as WebBrowser from "expo-web-browser";
import { colors, typography } from "@porterchain/mobile-theme";
import {
  fetchDashboard,
  formatCad,
  getQuote,
  pollCheckout,
  retryPayment,
  type CustomerDashboard,
  type QuoteResult,
} from "../api";
import { humanCustomerError } from "../errors";
import { EmptyState, type MotionName } from "../ui/Motion";
import { Screen } from "../ui/Screen";

type Segment = "orders" | "bookings" | "parcels" | "billing";

export function ActivityScreen({ onTrack }: { onTrack: (tracking: string) => void }) {
  const [segment, setSegment] = useState<Segment>("orders");
  const [data, setData] = useState<CustomerDashboard | null>(null);
  const [quotes, setQuotes] = useState<Record<string, QuoteResult>>({});
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(() => {
    void fetchDashboard()
      .then((dashboard) => {
        setData(dashboard);
        setError(null);
      })
      .catch((err: unknown) => {
        setError(humanCustomerError(err instanceof Error ? err.message : "request_failed"));
      });
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  useEffect(() => {
    if (segment !== "parcels" || !data) return;
    for (const booking of data.bookings) {
      if (!booking.quote_id || quotes[booking.quote_id]) continue;
      const quoteId = booking.quote_id;
      void getQuote(quoteId)
        .then((quote) => setQuotes((current) => ({ ...current, [quote.quote_id]: quote })))
        .catch(() =>
          setQuotes((current) => ({
            ...current,
            [quoteId]: {
              quote_id: quoteId,
              state: "unknown",
              amount_cents: 0,
              amount_display: "",
              expires_at: "",
              pricing_breakdown: [],
              vehicle_class: "—",
              package_type: "Unavailable",
            },
          }))
        );
    }
  }, [data, quotes, segment]);

  async function retry(quoteId: string) {
    try {
      const payment = await retryPayment(quoteId);
      if (payment.checkout_url) await WebBrowser.openBrowserAsync(payment.checkout_url);
      await pollCheckout(quoteId);
      load();
    } catch (err) {
      setError(humanCustomerError(err instanceof Error ? err.message : "request_failed"));
    }
  }

  return (
    <Screen>
      <Text style={styles.title}>Activity</Text>
      <ScrollView horizontal contentContainerStyle={styles.segments}>
        {(["orders", "bookings", "parcels", "billing"] as Segment[]).map((id) => (
          <Pressable key={id} onPress={() => setSegment(id)}>
            <Text style={segment === id ? styles.active : styles.segment}>{id}</Text>
          </Pressable>
        ))}
      </ScrollView>
      {error ? <Text style={styles.error}>{error}</Text> : null}
      <ScrollView contentContainerStyle={styles.list}>
        {segment === "orders"
          ? (data?.orders ?? []).map((order) => (
              <Pressable
                key={order.order_id}
                onPress={() => onTrack(order.tracking_number)}
                style={styles.row}
              >
                <Text style={styles.strong}>{order.tracking_number}</Text>
                <Text style={styles.meta}>
                  {order.state}
                  {order.amount_cents != null
                    ? ` · ${formatCad(order.amount_cents, order.currency)}`
                    : ""}
                </Text>
              </Pressable>
            ))
          : null}
        {segment === "bookings"
          ? (data?.bookings ?? []).map((booking) => (
              <Text key={booking.booking_id} style={styles.rowText}>
                {booking.booking_number || booking.booking_id} · {booking.state}
              </Text>
            ))
          : null}
        {segment === "parcels"
          ? (data?.bookings ?? []).map((booking) => {
              const quote = booking.quote_id ? quotes[booking.quote_id] : undefined;
              return (
                <Text key={booking.booking_id} style={styles.rowText}>
                  {quote
                    ? quote.booking_mode === "vehicle"
                      ? `Whole vehicle · ${quote.vehicle_class}`
                      : `${quote.parcels?.length || 0} parcels · ${quote.vehicle_class}${
                          quote.declared_value_cents
                            ? ` · $${(quote.declared_value_cents / 100).toFixed(2)}`
                            : ""
                        }`
                    : "Loading parcel…"}
                </Text>
              );
            })
          : null}
        {segment === "billing" ? (
          <>
            {(data?.invoices ?? []).map((invoice) => (
              <Pressable
                key={invoice.invoice_id}
                onPress={() => {
                  const url = invoice.stripe_receipt_url || invoice.pdf_url;
                  if (url) void Linking.openURL(url);
                }}
              >
                <Text style={styles.rowText}>
                  {invoice.invoice_number} · {formatCad(invoice.amount_cents, invoice.currency)}
                </Text>
              </Pressable>
            ))}
            {(data?.payments ?? []).map((payment) => (
              <Pressable
                key={payment.payment_id}
                onPress={() =>
                  payment.quote_id && payment.status !== "succeeded"
                    ? void retry(payment.quote_id)
                    : undefined
                }
              >
                <Text style={styles.rowText}>
                  {payment.status} · {formatCad(payment.amount_cents, payment.currency)}
                  {payment.failure_reason ? ` · ${payment.failure_reason}` : ""}
                  {payment.status !== "succeeded" && payment.quote_id ? " · Retry" : ""}
                </Text>
              </Pressable>
            ))}
          </>
        ) : null}
        {data && isEmpty(segment, data) ? (
          <EmptyState
            animation={EMPTY[segment].animation}
            title={EMPTY[segment].title}
            body={EMPTY[segment].body}
          />
        ) : null}
      </ScrollView>
    </Screen>
  );
}

const EMPTY: Record<Segment, { animation?: MotionName; title: string; body: string }> = {
  orders: {
    animation: "shipment",
    title: "No shipments yet",
    body: "Book a delivery and the order shows up here.",
  },
  bookings: {
    animation: "route",
    title: "No bookings yet",
    body: "Quotes you pay for are listed in this tab.",
  },
  parcels: {
    animation: "shipment",
    title: "No parcels yet",
    body: "Package, weight, and vehicle appear after a booking.",
  },
  billing: {
    title: "No invoices yet",
    body: "Receipts and payments show up after checkout.",
  },
};

function isEmpty(segment: Segment, data: CustomerDashboard) {
  if (segment === "orders") return data.orders.length === 0;
  if (segment === "bookings" || segment === "parcels") return data.bookings.length === 0;
  return data.invoices.length === 0 && data.payments.length === 0;
}

const styles = StyleSheet.create({
  title: { ...typography.title, fontSize: 30, color: colors.primary },
  segments: { gap: 12, paddingVertical: 8 },
  segment: {
    ...typography.caption,
    color: colors.muted,
    textTransform: "capitalize",
    backgroundColor: colors.white,
    overflow: "hidden",
    borderRadius: 999,
    paddingHorizontal: 14,
    paddingVertical: 8,
  },
  active: {
    ...typography.caption,
    color: colors.white,
    fontWeight: "700",
    textTransform: "capitalize",
    backgroundColor: colors.secondary,
    overflow: "hidden",
    borderRadius: 999,
    paddingHorizontal: 14,
    paddingVertical: 8,
  },
  list: { gap: 8, paddingBottom: 24 },
  row: { backgroundColor: colors.white, borderRadius: 12, padding: 12 },
  rowText: { ...typography.body, color: colors.primary },
  strong: { ...typography.body, color: colors.primary, fontWeight: "700" },
  meta: { ...typography.caption, color: colors.muted },
  error: { ...typography.caption, color: colors.danger },
});
