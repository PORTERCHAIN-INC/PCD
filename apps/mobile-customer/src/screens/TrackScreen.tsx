import { useState } from "react";
import { Pressable, Text, TextInput, StyleSheet } from "react-native";
import { colors, radius, spacing, touchTargetMin, typography } from "@porterchain/mobile-theme";
import {
  getOrderByTracking,
  getOrderLiveTracking,
  type OrderLiveTracking,
  type OrderResult,
} from "../api";
import { humanCustomerError } from "../errors";
import { Motion } from "../ui/Motion";
import { PrimaryButton } from "../ui/PrimaryButton";
import { Screen } from "../ui/Screen";

type Props = {
  initialTracking?: string;
  onBack?: () => void;
};

export function TrackScreen({ initialTracking = "", onBack }: Props) {
  const [trackingNumber, setTrackingNumber] = useState(initialTracking);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [order, setOrder] = useState<OrderResult | null>(null);
  const [live, setLive] = useState<OrderLiveTracking | null>(null);

  const trimmed = trackingNumber.trim();
  const status = live?.live_tracking?.delivery_status?.label ?? order?.state ?? null;
  const eta = live?.live_tracking?.eta?.label ?? live?.live_tracking?.eta?.arrives_at ?? null;

  async function lookup() {
    if (!trimmed) return;
    setBusy(true);
    setError(null);
    try {
      const [orderResult, liveResult] = await Promise.all([
        getOrderByTracking(trimmed),
        getOrderLiveTracking(trimmed).catch(() => null),
      ]);
      setOrder(orderResult);
      setLive(liveResult);
    } catch (err) {
      setOrder(null);
      setLive(null);
      const msg = err instanceof Error ? err.message : "lookup_failed";
      setError(humanCustomerError(msg));
    } finally {
      setBusy(false);
    }
  }

  return (
    <Screen testID="mobile-track">
      {onBack ? (
        <Pressable accessibilityRole="button" onPress={onBack}>
          <Text style={styles.meta}>Back</Text>
        </Pressable>
      ) : null}
      {!order ? <Motion name="shipment" size={140} /> : null}
      <Text style={styles.title}>Track delivery</Text>
      <Text style={styles.lede}>
        Enter a tracking number. Status and ETA come from Porterchain.
      </Text>
      <TextInput
        accessibilityLabel="Tracking number"
        placeholder="Tracking number"
        placeholderTextColor={colors.muted}
        autoCapitalize="characters"
        autoCorrect={false}
        style={styles.input}
        testID="tracking-input"
        value={trackingNumber}
        onChangeText={setTrackingNumber}
        onSubmitEditing={() => void lookup()}
      />
      <PrimaryButton
        testID="track-lookup"
        disabled={busy || !trimmed}
        label={busy ? "Looking up…" : trimmed ? `Track ${trimmed}` : "Enter a tracking number"}
        onPress={() => void lookup()}
      />
      {error ? <Text style={styles.error}>{error}</Text> : null}
      {order ? (
        <>
          <Text style={styles.kicker}>Shipment</Text>
          <Text style={styles.status}>{status ?? order.state}</Text>
          <Text style={styles.meta}>{order.order_number}</Text>
          {order.goods_summary ? <Text style={styles.meta}>{order.goods_summary}</Text> : null}
          {order.pickup?.formatted ? (
            <Text style={styles.meta}>Pickup: {order.pickup.formatted}</Text>
          ) : null}
          {order.dropoff?.formatted ? (
            <Text style={styles.meta}>Dropoff: {order.dropoff.formatted}</Text>
          ) : null}
          {eta ? <Text style={styles.meta}>ETA: {eta}</Text> : null}
          {order.tracking_page_message ? (
            <Text style={styles.meta}>{order.tracking_page_message}</Text>
          ) : null}
        </>
      ) : null}
    </Screen>
  );
}

const styles = StyleSheet.create({
  title: {
    ...typography.title,
    fontSize: 34,
    color: colors.primary,
  },
  lede: {
    ...typography.body,
    color: colors.muted,
  },
  input: {
    width: "100%",
    minHeight: touchTargetMin,
    borderWidth: 1,
    borderColor: `${colors.primary}26`,
    borderRadius: radius.lg,
    paddingHorizontal: spacing.md,
    paddingVertical: spacing.sm,
    fontSize: typography.body.fontSize,
    backgroundColor: colors.white,
    color: colors.primary,
  },
  error: {
    ...typography.caption,
    color: colors.danger,
  },
  kicker: {
    ...typography.caption,
    color: colors.muted,
    textTransform: "uppercase",
    letterSpacing: 1.1,
    marginTop: spacing.md,
  },
  status: {
    ...typography.title,
    color: colors.primary,
  },
  meta: {
    ...typography.caption,
    color: colors.muted,
  },
});
