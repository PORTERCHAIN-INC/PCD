import { useEffect, useMemo, useRef } from "react";
import { Platform, useColorScheme, View } from "react-native";
import MapView, { Marker, Polyline, PROVIDER_DEFAULT, PROVIDER_GOOGLE } from "react-native-maps";
import { radius, spacing, usePalette } from "../theme";
import { Txt } from "./kit";

type LatLng = { latitude: number; longitude: number };

type Props = {
  pickup: LatLng | null;
  dropoff: LatLng | null;
  driver: LatLng | null;
  eta: string | null;
  /** Short "updated 1 min ago" style note; position is coarse (~100 m). */
  note?: string | null;
};

/**
 * Native in-app live map: Apple Maps on iOS, Google Maps on Android.
 * Shows pickup (A), drop-off (B) and the driver's coarse latest position, with the ETA.
 */
export function LiveMap({ pickup, dropoff, driver, eta, note }: Props) {
  const c = usePalette();
  const scheme = useColorScheme() === "dark" ? "dark" : "light";
  const ref = useRef<MapView>(null);
  const points = useMemo(
    () => [pickup, dropoff, driver].filter((p): p is LatLng => p != null),
    [pickup, dropoff, driver]
  );

  useEffect(() => {
    if (points.length < 1) return;
    const t = setTimeout(
      () =>
        ref.current?.fitToCoordinates(points, {
          edgePadding: { top: 48, right: 48, bottom: 48, left: 48 },
          animated: false,
        }),
      250
    );
    return () => clearTimeout(t);
  }, [points]);

  if (points.length === 0) return null;
  const first = points[0]!;
  const a11y = [
    "Live map.",
    driver ? "Driver position shown." : "Driver position not available yet.",
    eta ? `Estimated arrival ${eta}.` : "",
  ].join(" ");

  return (
    <View
      testID="track-live-map"
      accessible
      accessibilityLabel={a11y}
      style={{ height: 240, borderRadius: radius.lg, overflow: "hidden" }}
    >
      <MapView
        ref={ref}
        style={{ flex: 1 }}
        provider={Platform.OS === "android" ? PROVIDER_GOOGLE : PROVIDER_DEFAULT}
        userInterfaceStyle={scheme}
        initialRegion={{ ...first, latitudeDelta: 0.3, longitudeDelta: 0.3 }}
        pitchEnabled={false}
        rotateEnabled={false}
        toolbarEnabled={false}
        showsPointsOfInterests={false}
        importantForAccessibility="no-hide-descendants"
        accessibilityElementsHidden
      >
        {pickup && dropoff ? (
          <Polyline
            coordinates={[pickup, dropoff]}
            strokeColor={c.secondary}
            strokeWidth={3}
            lineDashPattern={[6, 6]}
          />
        ) : null}
        {pickup ? <Marker coordinate={pickup} title="Pickup" pinColor="#2563eb" /> : null}
        {dropoff ? <Marker coordinate={dropoff} title="Drop-off" pinColor="#0a1628" /> : null}
        {driver ? (
          <Marker
            coordinate={driver}
            title="Driver"
            anchor={{ x: 0.5, y: 0.5 }}
            tracksViewChanges={false}
          >
            <View
              style={{
                width: 22,
                height: 22,
                borderRadius: 11,
                backgroundColor: c.secondary,
                borderWidth: 3,
                borderColor: "#ffffff",
              }}
            />
          </Marker>
        ) : null}
      </MapView>
      {eta ? (
        <View
          style={{
            position: "absolute",
            left: spacing.md,
            top: spacing.md,
            backgroundColor: c.white,
            borderRadius: radius.md,
            paddingHorizontal: spacing.md,
            paddingVertical: spacing.xs,
          }}
        >
          <Txt v="caption" tone="muted">
            ETA
          </Txt>
          <Txt v="headline">{eta}</Txt>
        </View>
      ) : null}
      {note ? (
        <View
          style={{
            position: "absolute",
            right: spacing.md,
            bottom: spacing.md,
            backgroundColor: c.white,
            borderRadius: radius.md,
            paddingHorizontal: spacing.sm,
            paddingVertical: 2,
          }}
        >
          <Txt v="caption" tone="muted">
            {note}
          </Txt>
        </View>
      ) : null}
    </View>
  );
}
