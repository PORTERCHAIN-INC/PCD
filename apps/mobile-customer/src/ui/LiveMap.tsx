import { useMemo } from "react";
import { useColorScheme, View } from "react-native";
import { Camera, GeoJSONSource, Layer, Map, Marker } from "@maplibre/maplibre-react-native";
import { radius, spacing, usePalette } from "../theme";
import { Txt } from "./kit";
import { boundsOf, porterchainNativeStyle, type LatLng } from "./mapStyle";

type Props = {
  pickup: LatLng | null;
  dropoff: LatLng | null;
  driver: LatLng | null;
  eta: string | null;
  /** Short "updated 1 min ago" style note; position is coarse (~100 m). */
  note?: string | null;
};

const lngLat = (p: LatLng): [number, number] => [p.longitude, p.latitude];

function Dot({ size, color }: { size: number; color: string }) {
  return (
    <View
      style={{
        width: size,
        height: size,
        borderRadius: size / 2,
        backgroundColor: color,
        borderWidth: 3,
        borderColor: "#ffffff",
      }}
    />
  );
}

/**
 * Native in-app live map on iOS and Android: MapLibre Native + self-hosted PMTiles
 * (doc 60 R4, no map vendor or key). Shows pickup, drop-off and the driver's coarse
 * latest position, with the ETA.
 */
export function LiveMap({ pickup, dropoff, driver, eta, note }: Props) {
  const c = usePalette();
  const scheme = useColorScheme() === "dark" ? "dark" : "light";
  const mapStyle = useMemo(() => porterchainNativeStyle(scheme), [scheme]);
  const points = useMemo(
    () => [pickup, dropoff, driver].filter((p): p is LatLng => p != null),
    [pickup, dropoff, driver]
  );
  const bounds = useMemo(() => boundsOf(points), [points]);

  if (!bounds) return null;
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
      <Map
        style={{ flex: 1 }}
        mapStyle={mapStyle}
        touchRotate={false}
        touchPitch={false}
        compass={false}
        logo={false}
        attribution
        importantForAccessibility="no-hide-descendants"
        accessibilityElementsHidden
      >
        <Camera bounds={bounds} padding={{ top: 48, right: 48, bottom: 48, left: 48 }} />
        {pickup && dropoff ? (
          <GeoJSONSource
            id="route"
            data={{
              type: "Feature",
              properties: {},
              geometry: { type: "LineString", coordinates: [lngLat(pickup), lngLat(dropoff)] },
            }}
          >
            <Layer
              id="route-line"
              type="line"
              paint={{ "line-color": c.secondary, "line-width": 3, "line-dasharray": [2, 2] }}
            />
          </GeoJSONSource>
        ) : null}
        {pickup ? (
          <Marker id="pickup" lngLat={lngLat(pickup)}>
            <Dot size={18} color="#2563eb" />
          </Marker>
        ) : null}
        {dropoff ? (
          <Marker id="dropoff" lngLat={lngLat(dropoff)}>
            <Dot size={18} color="#0a1628" />
          </Marker>
        ) : null}
        {driver ? (
          <Marker id="driver" lngLat={lngLat(driver)} anchor="center">
            <Dot size={22} color={c.secondary} />
          </Marker>
        ) : null}
      </Map>
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
