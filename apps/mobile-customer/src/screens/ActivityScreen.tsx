import { useState } from "react";
import { View } from "react-native";
import * as WebBrowser from "expo-web-browser";
import { vehicleLabel } from "@porterchain/types";
import { fetchDashboard, pollCheckout, retryPayment } from "../api";
import { humanCustomerError } from "../errors";
import {
  formatMoney,
  friendlyDate,
  isActiveState,
  orderStatus,
  paymentStatus,
  shortAddress,
} from "../format";
import { spacing } from "../theme";
import {
  Banner,
  Card,
  Chip,
  Divider,
  EmptyNote,
  ListRow,
  Segmented,
  SkeletonList,
  StatusPill,
  Txt,
} from "../ui/kit";
import { Screen } from "../ui/Screen";
import { useRemote } from "../ui/useRemote";
import { peekCachedDashboard } from "./HomeScreen";

type Segment = "shipments" | "receipts";
type Filter = "all" | "active" | "done";

export function ActivityScreen({
  onTrack,
  onBook,
}: {
  onTrack: (tracking: string) => void;
  onBook?: () => void;
}) {
  const [segment, setSegment] = useState<Segment>("shipments");
  const [filter, setFilter] = useState<Filter>("all");
  const [notice, setNotice] = useState<string | null>(null);
  const { data, loading, refreshing, error, offline, refresh } = useRemote(
    fetchDashboard,
    peekCachedDashboard()
  );

  async function retry(quoteId: string) {
    setNotice(null);
    try {
      const payment = await retryPayment(quoteId);
      if (payment.checkout_url) await WebBrowser.openBrowserAsync(payment.checkout_url);
      await pollCheckout(quoteId);
      void refresh();
    } catch (err) {
      setNotice(humanCustomerError(err instanceof Error ? err.message : "request_failed"));
    }
  }

  const orders = (data?.orders ?? []).filter((o) =>
    filter === "all" ? true : filter === "active" ? isActiveState(o.state) : !isActiveState(o.state)
  );
  const failed = (data?.payments ?? []).filter(
    (p) => p.quote_id && paymentStatus(p.status).tone === "danger"
  );

  return (
    <Screen
      scroll
      testID="activity"
      title="Activity"
      refreshing={refreshing}
      onRefresh={() => void refresh()}
    >
      <Segmented
        options={[
          { id: "shipments", label: "Shipments" },
          { id: "receipts", label: "Receipts" },
        ]}
        value={segment}
        onChange={setSegment}
      />
      {error ? (
        <Banner
          tone={offline ? "offline" : "danger"}
          text={error}
          action="Retry"
          onAction={() => void refresh()}
        />
      ) : null}
      {notice ? <Banner tone="danger" text={notice} /> : null}
      {failed.length ? (
        <Banner
          tone="warning"
          text={`${failed.length} payment${failed.length > 1 ? "s" : ""} didn't go through.`}
          action="Pay now"
          onAction={() => void retry(failed[0]!.quote_id!)}
        />
      ) : null}
      {loading && !data ? <SkeletonList rows={4} /> : null}

      {data && segment === "shipments" ? (
        <>
          <View style={{ flexDirection: "row", gap: spacing.sm }}>
            <Chip label="All" selected={filter === "all"} onPress={() => setFilter("all")} />
            <Chip
              label="In progress"
              selected={filter === "active"}
              onPress={() => setFilter("active")}
            />
            <Chip
              label="Completed"
              selected={filter === "done"}
              onPress={() => setFilter("done")}
            />
          </View>
          {orders.length === 0 ? (
            <EmptyNote
              icon="cube-outline"
              title={filter === "all" ? "No shipments yet" : "Nothing here"}
              body={
                filter === "all"
                  ? "Book a delivery and it shows up here with live tracking."
                  : "Try another filter."
              }
              action={filter === "all" && onBook ? "Book a delivery" : undefined}
              onAction={onBook}
            />
          ) : (
            <Card style={{ paddingVertical: spacing.xs, gap: 0 }}>
              {orders.map((order, i) => {
                const s = orderStatus(order.state);
                return (
                  <View key={order.order_id}>
                    {i ? <Divider /> : null}
                    <ListRow
                      title={`${shortAddress(order.pickup?.formatted) || order.tracking_number} → ${shortAddress(order.dropoff?.formatted)}`}
                      subtitle={[
                        friendlyDate(order.created_at),
                        order.goods_summary,
                        order.vehicle_class
                          ? vehicleLabel(order.vehicle_class, order.vehicle_class)
                          : "",
                        order.amount_cents != null
                          ? formatMoney(order.amount_cents, order.currency)
                          : "",
                      ]
                        .filter(Boolean)
                        .join(" · ")}
                      right={<StatusPill label={s.label} tone={s.tone} />}
                      onPress={() => onTrack(order.tracking_number)}
                    />
                  </View>
                );
              })}
            </Card>
          )}
        </>
      ) : null}

      {data && segment === "receipts" ? (
        data.invoices.length === 0 && data.payments.length === 0 ? (
          <EmptyNote
            icon="receipt-outline"
            title="No receipts yet"
            body="Stripe receipts and invoices appear here after you pay."
          />
        ) : (
          <>
            {data.invoices.length ? (
              <Card style={{ paddingVertical: spacing.xs, gap: 0 }}>
                {data.invoices.map((invoice, i) => {
                  const url = invoice.stripe_receipt_url || invoice.pdf_url;
                  return (
                    <View key={invoice.invoice_id}>
                      {i ? <Divider /> : null}
                      <ListRow
                        icon="document-text-outline"
                        title={`Invoice ${invoice.invoice_number}`}
                        subtitle={[
                          friendlyDate(invoice.created_at),
                          url ? "Tap to view receipt" : "Receipt not ready",
                        ]
                          .filter(Boolean)
                          .join(" · ")}
                        right={
                          <Txt v="headline">
                            {formatMoney(invoice.amount_cents, invoice.currency)}
                          </Txt>
                        }
                        onPress={url ? () => void WebBrowser.openBrowserAsync(url) : undefined}
                      />
                    </View>
                  );
                })}
              </Card>
            ) : null}
            {data.payments.length ? (
              <>
                <Txt v="overline" tone="muted" style={{ marginTop: spacing.sm }}>
                  Card payments (Stripe)
                </Txt>
                <Card style={{ paddingVertical: spacing.xs, gap: 0 }}>
                  {data.payments.map((payment, i) => {
                    const s = paymentStatus(payment.status);
                    const canRetry = Boolean(payment.quote_id) && s.tone === "danger";
                    return (
                      <View key={payment.payment_id}>
                        {i ? <Divider /> : null}
                        <ListRow
                          icon="card-outline"
                          title={formatMoney(payment.amount_cents, payment.currency)}
                          subtitle={
                            canRetry
                              ? `${payment.failure_reason ?? "Declined"} · Tap to pay again`
                              : payment.receipt_url
                                ? "Tap to view receipt"
                                : undefined
                          }
                          right={<StatusPill label={s.label} tone={s.tone} />}
                          onPress={
                            canRetry
                              ? () => void retry(payment.quote_id!)
                              : payment.receipt_url
                                ? () => void WebBrowser.openBrowserAsync(payment.receipt_url!)
                                : undefined
                          }
                        />
                      </View>
                    );
                  })}
                </Card>
              </>
            ) : null}
          </>
        )
      ) : null}
    </Screen>
  );
}
