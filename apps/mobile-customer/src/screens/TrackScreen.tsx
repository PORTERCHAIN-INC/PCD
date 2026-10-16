import { useCallback, useEffect, useState } from "react";
import { Pressable, Share, TextInput, View } from "react-native";
import * as WebBrowser from "expo-web-browser";
import {
  etaWindowText,
  isEnhancedExperience,
  safeBrandColor,
  statusHeadline,
  stopsAwayText,
  type TrackingExperience,
} from "@porterchain/types";
import {
  getOrderByTracking,
  getOrderExperience,
  getDriverPosition,
  getOrderLiveTracking,
  type OrderLiveTracking,
  type OrderResult,
} from "../api";
import { websiteUrl } from "../config";
import { LiveMap } from "../ui/LiveMap";
import { openDocuments } from "../documents";
import { humanCustomerError } from "../errors";
import { isActiveState, isOfflineError, JOURNEY, orderStatus, shortAddress } from "../format";
import { haptic } from "../haptics";
import { radius, spacing, touchTargetMin, type, usePalette } from "../theme";
import { Banner, Button, Card, Divider, Icon, ListRow, Progress, Skeleton, Txt } from "../ui/kit";
import { Screen } from "../ui/Screen";

type Props = {
  initialTracking?: string;
  onBack?: () => void;
};

/** The one public tracking page (map, driver position, photo proof) lives on porterchain.com. */
export function trackingUrl(tracking: string): string {
  return `${websiteUrl}/en/track/${encodeURIComponent(tracking)}`;
}

export function TrackScreen({ initialTracking = "", onBack }: Props) {
  const c = usePalette();
  const [trackingNumber, setTrackingNumber] = useState(initialTracking);
  const [busy, setBusy] = useState(false);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [offline, setOffline] = useState(false);
  const [order, setOrder] = useState<OrderResult | null>(null);
  const [live, setLive] = useState<OrderLiveTracking | null>(null);
  const [experience, setExperience] = useState<TrackingExperience | null>(null);
  const [driver, setDriver] = useState<{ latitude: number; longitude: number; at: string } | null>(
    null
  );
  const enhanced = isEnhancedExperience(experience) ? experience : null;

  const trimmed = trackingNumber.trim();
  const status = orderStatus(order?.state);
  const headline = enhanced
    ? statusHeadline(enhanced)
    : (live?.live_tracking?.delivery_status?.label ?? status.label);
  const eta = live?.live_tracking?.eta?.label ?? null;
  const tracking = order?.tracking_number ?? trimmed;

  const lookup = useCallback(async (number: string, mode: "lookup" | "refresh" = "lookup") => {
    const n = number.trim();
    if (!n) return;
    if (mode === "lookup") setBusy(true);
    else setRefreshing(true);
    try {
      const [orderResult, liveResult, experienceResult] = await Promise.all([
        getOrderByTracking(n),
        getOrderLiveTracking(n).catch(() => null),
        getOrderExperience(n).catch(() => null),
      ]);
      setOrder(orderResult);
      setLive(liveResult);
      setExperience(experienceResult);
      setError(null);
      setOffline(false);
      if (mode === "lookup") haptic.success();
    } catch (err) {
      const msg = err instanceof Error ? err.message : "lookup_failed";
      setOffline(isOfflineError(msg));
      if (mode === "lookup") {
        setOrder(null);
        setLive(null);
        setExperience(null);
        haptic.error();
      }
      setError(humanCustomerError(msg));
    } finally {
      setBusy(false);
      setRefreshing(false);
    }
  }, []);

  // Opened from a shipment or a link: look it up straight away (no extra tap).
  useEffect(() => {
    if (initialTracking.trim()) void lookup(initialTracking);
  }, [initialTracking, lookup]);

  // Keep an active delivery fresh while the screen is open.
  useEffect(() => {
    if (!order || !isActiveState(order.state)) return;
    const timer = setInterval(() => void lookup(order.tracking_number, "refresh"), 30_000);
    return () => clearInterval(timer);
  }, [order, lookup]);

  const active = !!order && isActiveState(order.state);
  // Driver's coarse live position: own active shipment only; ~10 s poll (server rate-limits at 5 s).
  useEffect(() => {
    if (!order || !active) {
      setDriver(null);
      return;
    }
    let stop = false;
    const tick = () =>
      getDriverPosition(order.tracking_number)
        .then((r) => {
          if (stop) return;
          setDriver(
            r.available && r.position
              ? { latitude: r.position.lat, longitude: r.position.lng, at: r.position.recorded_at }
              : null
          );
        })
        .catch(() => undefined);
    void tick();
    const timer = setInterval(tick, 10_000);
    return () => {
      stop = true;
      clearInterval(timer);
    };
  }, [order, active]);

  const pt = (a?: { lat?: number | null; lng?: number | null } | null) =>
    a?.lat != null && a.lng != null ? { latitude: a.lat, longitude: a.lng } : null;
  const pickupPt = order ? pt(order.pickup) : null;
  const dropPt = order ? pt(order.dropoff) : null;
  const showMap = active && (pickupPt || dropPt);
  const driverNote = driver
    ? `Updated ${Math.max(0, Math.round((Date.now() - Date.parse(driver.at)) / 60_000))} min ago`
    : "Waiting for driver location";

  return (
    <Screen
      scroll
      testID="mobile-track"
      refreshing={refreshing}
      onRefresh={order ? () => void lookup(tracking, "refresh") : undefined}
    >
      {onBack ? (
        <Pressable
          accessibilityRole="button"
          accessibilityLabel="Back"
          onPress={onBack}
          hitSlop={8}
          style={{
            minHeight: touchTargetMin,
            flexDirection: "row",
            alignItems: "center",
            gap: 4,
            alignSelf: "flex-start",
          }}
        >
          <Icon name="chevron-back" size={22} color={c.accentText} />
          <Txt v="headline" tone="accent">
            Back
          </Txt>
        </Pressable>
      ) : null}
      <Txt v="largeTitle" accessibilityRole="header">
        Track delivery
      </Txt>
      <View
        style={{
          flexDirection: "row",
          alignItems: "center",
          gap: spacing.sm,
          backgroundColor: c.white,
          borderRadius: radius.lg,
          borderWidth: 1,
          borderColor: c.border,
          paddingHorizontal: spacing.md,
        }}
      >
        <Icon name="search" size={18} color={c.muted} />
        <TextInput
          accessibilityLabel="Tracking number"
          placeholder="Tracking number, e.g. PC-20261015-F4BC86"
          placeholderTextColor={c.muted}
          autoCapitalize="characters"
          autoCorrect={false}
          returnKeyType="search"
          maxFontSizeMultiplier={1.6}
          style={[type.body, { flex: 1, minHeight: 48, color: c.primary }]}
          testID="tracking-input"
          value={trackingNumber}
          onChangeText={setTrackingNumber}
          onSubmitEditing={() => void lookup(trackingNumber)}
        />
      </View>
      {!order || trimmed !== order.tracking_number ? (
        <Button
          testID="track-lookup"
          disabled={!trimmed}
          loading={busy}
          label={trimmed ? `Track ${trimmed}` : "Enter a tracking number"}
          onPress={() => void lookup(trackingNumber)}
        />
      ) : null}
      {error ? (
        <Banner
          tone={offline ? "offline" : "danger"}
          text={error}
          action={order ? "Retry" : undefined}
          onAction={() => void lookup(tracking)}
        />
      ) : null}
      {busy && !order ? (
        <Card>
          <Skeleton width="60%" height={22} />
          <Skeleton height={6} />
          <Skeleton width="40%" />
        </Card>
      ) : null}

      {order ? (
        <>
          <Card testID="track-status" style={{ gap: spacing.md }}>
            {enhanced?.branding.company_name ? (
              <View
                testID="track-experience"
                style={{
                  backgroundColor: safeBrandColor(enhanced.branding.primary_color),
                  borderRadius: radius.md,
                  padding: spacing.sm,
                }}
              >
                <Txt v="caption" style={{ color: "#fff" }}>
                  Delivering for {enhanced.branding.company_name}
                </Txt>
              </View>
            ) : null}
            <View style={{ flexDirection: "row", alignItems: "flex-start", gap: spacing.md }}>
              <View style={{ flex: 1, gap: 4 }}>
                <Txt v="title">{headline}</Txt>
                <Txt v="caption" tone="muted">
                  {order.order_number} · {order.tracking_number}
                </Txt>
              </View>
              {eta ? (
                <View
                  accessible
                  accessibilityLabel={`Estimated arrival ${eta}`}
                  style={{ alignItems: "flex-end" }}
                >
                  <Txt v="overline" tone="muted">
                    ETA
                  </Txt>
                  <Txt v="title" tone="accent">
                    {eta}
                  </Txt>
                </View>
              ) : null}
            </View>
            <Progress steps={JOURNEY} current={status.step} />
            <View style={{ flexDirection: "row", justifyContent: "space-between" }}>
              <Txt v="caption" tone="muted">
                Booked
              </Txt>
              <Txt v="caption" tone="muted">
                Delivered
              </Txt>
            </View>
            {enhanced && etaWindowText(enhanced.eta_window) ? (
              <Txt v="callout" tone="muted">
                Delivery window: {etaWindowText(enhanced.eta_window)}
              </Txt>
            ) : null}
            {enhanced && stopsAwayText(enhanced.stops_away, enhanced.state) ? (
              <Txt v="callout" tone="muted">
                {stopsAwayText(enhanced.stops_away, enhanced.state)}
              </Txt>
            ) : null}
          </Card>

          {showMap ? (
            <LiveMap
              pickup={pickupPt}
              dropoff={dropPt}
              driver={driver ? { latitude: driver.latitude, longitude: driver.longitude } : null}
              eta={eta}
              note={driverNote}
            />
          ) : null}

          <Card
            testID="track-open-live"
            accessibilityLabel="Open the tracking page on porterchain.com"
            onPress={() => void WebBrowser.openBrowserAsync(trackingUrl(tracking))}
            style={{ padding: 0, overflow: "hidden", gap: 0 }}
          >
            <View
              style={{
                flexDirection: "row",
                alignItems: "center",
                padding: spacing.lg,
                gap: spacing.sm,
              }}
            >
              <View style={{ flex: 1 }}>
                <Txt v="headline">Open on porterchain.com</Txt>
                <Txt v="caption" tone="muted">
                  Share link, photo proof and receipt
                </Txt>
              </View>
              <Icon name="open-outline" size={20} color={c.accentText} />
            </View>
          </Card>

          <Card style={{ paddingVertical: spacing.xs, gap: 0 }}>
            {enhanced?.driver?.name ? (
              <>
                <ListRow icon="person" title={enhanced.driver.name} subtitle="Your driver" />
                <Divider />
              </>
            ) : null}
            <ListRow
              icon="arrow-up-circle"
              title={shortAddress(order.pickup?.formatted) || "Pickup"}
              subtitle={order.pickup?.formatted ?? undefined}
            />
            <Divider />
            <ListRow
              icon="flag"
              title={shortAddress(order.dropoff?.formatted) || "Drop-off"}
              subtitle={order.dropoff?.formatted ?? undefined}
            />
          </Card>

          {enhanced?.rules.id_required ? (
            <Banner tone="warning" text="Photo ID is required at delivery." />
          ) : null}
          {enhanced?.proof_of_delivery ? (
            <Banner
              tone="success"
              text={`Delivered${enhanced.proof_of_delivery.received_by ? ` · received by ${enhanced.proof_of_delivery.received_by}` : ""}${
                enhanced.proof_of_delivery.proof_types.length
                  ? ` · proof: ${enhanced.proof_of_delivery.proof_types.join(", ")}`
                  : ""
              }`}
            />
          ) : null}

          {enhanced?.timeline.length ? (
            <Card>
              <Txt v="headline" accessibilityRole="header">
                Timeline
              </Txt>
              {enhanced.timeline
                .slice()
                .reverse()
                .map((item, i) => (
                  <View
                    key={`${item.code}-${i}`}
                    style={{ flexDirection: "row", gap: spacing.md, alignItems: "flex-start" }}
                  >
                    <View
                      style={{
                        width: 10,
                        height: 10,
                        borderRadius: 5,
                        marginTop: 6,
                        backgroundColor: i === 0 ? c.secondary : c.border,
                      }}
                    />
                    <View style={{ flex: 1 }}>
                      <Txt v="callout">{item.label}</Txt>
                      {item.at ? (
                        <Txt v="caption" tone="muted">
                          {new Date(item.at).toLocaleString("en-CA", {
                            timeZone: "America/Toronto",
                          })}
                        </Txt>
                      ) : null}
                    </View>
                  </View>
                ))}
            </Card>
          ) : null}

          {order.tracking_page_message ? (
            <Banner tone="info" text={order.tracking_page_message} />
          ) : null}

          <Card style={{ paddingVertical: spacing.xs, gap: 0 }}>
            <ListRow
              testID="track-attach-docs"
              icon="document-attach-outline"
              title="Pickup documents"
              subtitle="Add or view documents the driver shows at pickup"
              onPress={() => void openDocuments(tracking)}
            />
            <Divider />
            <ListRow
              icon="share-outline"
              title="Share tracking link"
              subtitle="porterchain.com tracking page"
              onPress={() => void Share.share({ message: trackingUrl(tracking) })}
            />
            {enhanced?.help.email || enhanced?.help.phone ? (
              <>
                <Divider />
                <ListRow
                  icon="help-buoy-outline"
                  title="Need help?"
                  subtitle={[enhanced.help.email, enhanced.help.phone].filter(Boolean).join(" · ")}
                />
              </>
            ) : null}
          </Card>
          {enhanced?.self_service.available ? (
            <Txt v="caption" tone="muted" center>
              To change the time or add a gate code, use the link in your delivery message.
            </Txt>
          ) : null}
        </>
      ) : null}
    </Screen>
  );
}
