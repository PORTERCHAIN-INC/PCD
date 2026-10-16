"use client";

import "maplibre-gl/dist/maplibre-gl.css";
import { useEffect, useRef, useState } from "react";
import maplibregl, { type Map as MLMap, type Marker } from "maplibre-gl";
import { Protocol } from "pmtiles";
import { layers, namedFlavor } from "@protomaps/basemaps";
import circle from "@turf/circle";
import bbox from "@turf/bbox";
import { lineString, featureCollection, point } from "@turf/helpers";
import { GTA_CENTER, resolveTilesBase } from "./maps-core";
import type { LatLng } from "./types";

export type MapMarkerKind = "pickup" | "dropoff" | "driver" | "driver-lg" | "device";
export type MapMarker = { position: LatLng; kind: MapMarkerKind; title?: string };
export type MapLine = { path: LatLng[]; color: string; width: number; opacity: number };
export type MapCircle = { center: LatLng; radiusM: number; color: string; strokeOpacity?: number };

let protocolAdded = false;
function ensureProtocol() {
  if (protocolAdded) return;
  const protocol = new Protocol();
  maplibregl.addProtocol("pmtiles", protocol.tile);
  protocolAdded = true;
}

export function porterchainMapStyle(tilesBase?: string): maplibregl.StyleSpecification {
  const base = resolveTilesBase(tilesBase);
  return {
    version: 8,
    glyphs: `${base}/fonts/{fontstack}/{range}.pbf`,
    sprite: `${base}/sprites/v4/light`,
    sources: {
      protomaps: {
        type: "vector",
        url: `pmtiles://${base}/gta-150km.pmtiles`,
        attribution: '© <a href="https://openstreetmap.org/copyright">OpenStreetMap</a>',
      },
    },
    // @protomaps/basemaps types its layers with its own copy of the style spec; the
    // shapes are identical, so widen to maplibre-gl's type (fails the Docker build otherwise).
    layers: layers("protomaps", namedFlavor("light"), {
      lang: "en",
    }) as unknown as maplibregl.LayerSpecification[],
  };
}

function markerEl(kind: MapMarkerKind, title?: string): HTMLElement {
  const el = document.createElement("div");
  if (title) el.title = title;
  const pill = (bg: string, text: string) => {
    el.textContent = text;
    Object.assign(el.style, {
      background: bg,
      color: "#fff",
      borderRadius: "9999px",
      padding: "2px 8px",
      fontSize: "10px",
      fontWeight: "700",
      lineHeight: "16px",
      boxShadow: "0 1px 2px rgba(0,0,0,.25)",
    });
  };
  const dot = (size: number, bg: string, border: string) =>
    Object.assign(el.style, {
      width: `${size}px`,
      height: `${size}px`,
      borderRadius: "9999px",
      background: bg,
      border,
      boxShadow: "0 1px 3px rgba(0,0,0,.35)",
    });
  if (kind === "pickup") pill("#16a34a", "P");
  else if (kind === "dropoff") pill("#dc2626", "D");
  else if (kind === "driver") dot(12, "#2563eb", "2px solid #fff");
  else if (kind === "driver-lg") dot(16, "#2563eb", "2px solid #fff");
  else dot(10, "#38bdf8", "1px solid #fff");
  return el;
}

export type LibreMapProps = {
  center?: LatLng;
  zoom?: number;
  markers?: MapMarker[];
  lines?: MapLine[];
  circles?: MapCircle[];
  fitPoints?: LatLng[];
  minFitPoints?: number;
  fitPadding?: number;
  /** "cooperative" = ctrl/two-finger to zoom (embedded cards); "greedy" = full gestures. */
  gestureHandling?: "cooperative" | "greedy";
  tilesBase?: string;
  style?: React.CSSProperties;
};

export default function LibreMap({
  center,
  zoom = 12,
  markers = [],
  lines = [],
  circles = [],
  fitPoints = [],
  minFitPoints = 2,
  fitPadding = 48,
  gestureHandling = "greedy",
  tilesBase,
  style,
}: LibreMapProps) {
  const ref = useRef<HTMLDivElement>(null);
  const mapRef = useRef<MLMap | null>(null);
  const markerRefs = useRef<Marker[]>([]);
  const [ready, setReady] = useState(false);

  useEffect(() => {
    if (!ref.current) return;
    ensureProtocol();
    const c = center ?? GTA_CENTER;
    const map = new maplibregl.Map({
      container: ref.current,
      style: porterchainMapStyle(tilesBase),
      center: [c.lng, c.lat],
      zoom,
      cooperativeGestures: gestureHandling === "cooperative",
      attributionControl: { compact: true },
    });
    map.addControl(new maplibregl.NavigationControl({ showCompass: false }), "bottom-right");
    map.on("load", () => setReady(true));
    mapRef.current = map;
    return () => {
      map.remove();
      mapRef.current = null;
      setReady(false);
    };
    // Map is created once; later prop changes update sources/markers below.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    const map = mapRef.current;
    if (!map || !ready) return;
    const lineFc = featureCollection(
      lines
        .filter((l) => l.path.length > 1)
        .map((l) =>
          lineString(
            l.path.map((p) => [p.lng, p.lat]),
            { color: l.color, width: l.width, opacity: l.opacity }
          )
        )
    );
    const circleFc = featureCollection(
      circles.map((c) =>
        circle([c.center.lng, c.center.lat], c.radiusM / 1000, {
          steps: 64,
          units: "kilometers",
          properties: { color: c.color, strokeOpacity: c.strokeOpacity ?? 0.5 },
        })
      )
    );
    const lineSrc = map.getSource("pc-lines") as maplibregl.GeoJSONSource | undefined;
    if (lineSrc) lineSrc.setData(lineFc);
    else {
      map.addSource("pc-lines", { type: "geojson", data: lineFc });
      map.addLayer({
        id: "pc-lines",
        type: "line",
        source: "pc-lines",
        layout: { "line-cap": "round", "line-join": "round" },
        paint: {
          "line-color": ["get", "color"],
          "line-width": ["get", "width"],
          "line-opacity": ["get", "opacity"],
        },
      });
    }
    const circleSrc = map.getSource("pc-circles") as maplibregl.GeoJSONSource | undefined;
    if (circleSrc) circleSrc.setData(circleFc);
    else {
      map.addSource("pc-circles", { type: "geojson", data: circleFc });
      map.addLayer({
        id: "pc-circles-fill",
        type: "fill",
        source: "pc-circles",
        paint: { "fill-color": ["get", "color"], "fill-opacity": 0.08 },
      });
      map.addLayer({
        id: "pc-circles-line",
        type: "line",
        source: "pc-circles",
        paint: {
          "line-color": ["get", "color"],
          "line-opacity": ["get", "strokeOpacity"],
          "line-width": 1,
        },
      });
    }
  }, [ready, lines, circles]);

  useEffect(() => {
    const map = mapRef.current;
    if (!map) return;
    markerRefs.current.forEach((m) => m.remove());
    markerRefs.current = markers.map((m) =>
      new maplibregl.Marker({ element: markerEl(m.kind, m.title) })
        .setLngLat([m.position.lng, m.position.lat])
        .addTo(map)
    );
  }, [markers]);

  const fitKey = JSON.stringify(fitPoints);
  useEffect(() => {
    const map = mapRef.current;
    if (!map || fitPoints.length < minFitPoints) return;
    if (fitPoints.length === 1) {
      map.jumpTo({ center: [fitPoints[0].lng, fitPoints[0].lat] });
      return;
    }
    const [w, s, e, n] = bbox(featureCollection(fitPoints.map((p) => point([p.lng, p.lat]))));
    map.fitBounds(
      [
        [w, s],
        [e, n],
      ],
      { padding: fitPadding, duration: 0, maxZoom: 16 }
    );
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [fitKey, minFitPoints, fitPadding]);

  return <div ref={ref} style={{ width: "100%", height: "100%", ...style }} />;
}
