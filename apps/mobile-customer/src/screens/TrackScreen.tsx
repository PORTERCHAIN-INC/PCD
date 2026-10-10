import { useState } from "react";
import { Linking, Pressable, Text, TextInput, StyleSheet, View } from "react-native";
import { websiteUrl } from "../config";
import {
  etaWindowText,
  isEnhancedExperience,
  safeBrandColor,
  statusHeadline,
  stopsAwayText,
  type TrackingExperience,
} from "@porterchain/types";
import { colors, radius, spacing, touchTargetMin, typography } from "@porterchain/mobile-theme";
import {
  getOrderByTracking,
  getOrderExperience,
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
  const [experience, setExperience] = useState<TrackingExperience | null>(null);
  const enhanced = isEnhancedExperience(experience) ? experience : null;

  const trimmed = trackingNumber.trim();
  const status = live?.live_tracking?.delivery_status?.label ?? order?.state ?? null;
  const eta = live?.live_tracking?.eta?.label ?? live?.live_tracking?.eta?.arrives_at ?? null;

  async function lookup() {
    if (!trimmed) return;
    setBusy(true);
    setError(null);
    try {
      const [orderResult, liveResult, experienceResult] = await Promise.all([
        getOrderByTracking(trimmed),
        getOrderLiveTracking(trimmed).catch(() => null),
        getOrderExperience(trimmed).catch(() => null),
      ]);
      setOrder(orderResult);
      setLive(liveResult);
      setExperience(experienceResult);
    } catch (err) {
      setOrder(null);
      setLive(null);
      setExperience(null);
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
          {enhanced ? (
            <View
              testID="track-experience"
              style={[
                styles.brandBar,
                { backgroundColor: safeBrandColor(enhanced.branding.primary_color) },
              ]}
            >
              {enhanced.branding.company_name ? (
                <Text style={styles.brandName}>{enhanced.branding.company_name}</Text>
              ) : null}
              <Text style={styles.brandStatus}>{statusHeadline(enhanced)}</Text>
            </View>
          ) : null}
          <Text style={styles.kicker}>Shipment</Text>
          <Text style={styles.status}>
            {enhanced ? statusHeadline(enhanced) : (status ?? order.state)}
          </Text>
          <Text style={styles.meta}>{order.order_number}</Text>
          <PrimaryButton
            testID="track-open-live"
            label="Open live map"
            onPress={() =>
              void Linking.openURL(`${websiteUrl}/en/track/${encodeURIComponent(order.tracking_number ?? trimmed)}`)
            }
          />
          {enhanced ? (
            <>
              {etaWindowText(enhanced.eta_window) ? (
                <Text style={styles.meta}>
                  Delivery window: {etaWindowText(enhanced.eta_window)}
                </Text>
              ) : null}
              {stopsAwayText(enhanced.stops_away, enhanced.state) ? (
                <Text style={styles.meta}>
                  {stopsAwayText(enhanced.stops_away, enhanced.state)}
                </Text>
              ) : null}
              {enhanced.driver?.name ? (
                <Text style={styles.meta}>Your driver: {enhanced.driver.name}</Text>
              ) : null}
              {enhanced.rules.id_required ? (
                <Text style={styles.meta}>Photo ID is required at delivery.</Text>
              ) : null}
              {enhanced.proof_of_delivery ? (
                <Text style={styles.meta}>
                  Delivered
                  {enhanced.proof_of_delivery.received_by
                    ? ` · received by ${enhanced.proof_of_delivery.received_by}`
                    : ""}
                  {enhanced.proof_of_delivery.proof_types.length
                    ? ` · proof: ${enhanced.proof_of_delivery.proof_types.join(", ")}`
                    : ""}
                </Text>
              ) : null}
              {enhanced.timeline
                .slice()
                .reverse()
                .map((item, i) => (
                  <Text key={`${item.code}-${i}`} style={styles.timeline}>
                    {item.label}
                    {item.at
                      ? ` · ${new Date(item.at).toLocaleString("en-CA", { timeZone: "America/Toronto" })}`
                      : ""}
                  </Text>
                ))}
              {enhanced.help.email || enhanced.help.phone ? (
                <Text style={styles.meta}>
                  Need help?{" "}
                  {[enhanced.help.email, enhanced.help.phone].filter(Boolean).join(" · ")}
                </Text>
              ) : null}
              {enhanced.self_service.available ? (
                <Text style={styles.meta}>
                  To change the time or add a gate code, use the link in your delivery message.
                </Text>
              ) : null}
            </>
          ) : null}
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
  timeline: {
    ...typography.caption,
    color: colors.primary,
  },
  brandBar: {
    width: "100%",
    borderRadius: radius.lg,
    padding: spacing.md,
    marginTop: spacing.md,
  },
  brandName: {
    ...typography.caption,
    color: colors.white,
  },
  brandStatus: {
    ...typography.title,
    color: colors.white,
  },
});
