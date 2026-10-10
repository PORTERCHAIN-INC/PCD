"use client";

import { useEffect, useRef } from "react";
import * as maplibregl from "maplibre-gl";
import type { GeoJSONSource, LngLatLike, MapLayerMouseEvent, Map as MlMap } from "maplibre-gl";
import "maplibre-gl/dist/maplibre-gl.css";

/** OpenStreetMap raster tiles (no API key). Point NEXT_PUBLIC_MAP_TILE_URL at self-hosted tiles in production. */
const TILE_URL =
  process.env.NEXT_PUBLIC_MAP_TILE_URL || "https://tile.openstreetmap.org/{z}/{x}/{y}.png";
const GTA: [number, number] = [-79.3832, 43.6532];

export type MapPoint = {
  id: string;
  lat: number;
  lng: number;
  color: string;
  size?: number;
  title?: string;
  ring?: string;
};
export type MapLine = {
  id: string;
  path: [number, number][];
  color: string;
  width?: number;
  opacity?: number;
};
export type MapArea = { id: string; path: [number, number][]; color: string };
export type MapHeat = { lat: number; lng: number; weight: number };

type Props = {
  points?: MapPoint[];
  lines?: MapLine[];
  areas?: MapArea[];
  heat?: MapHeat[];
  /** Fit to these points whenever their count changes. */
  fit?: boolean;
  onPointClick?: (id: string) => void;
  className?: string;
  label: string;
};

type Data = Parameters<GeoJSONSource["setData"]>[0];
type Feature = {
  type: "Feature";
  geometry: { type: "Point" | "LineString" | "Polygon"; coordinates: unknown };
  properties: Record<string, unknown>;
};
const fc = (features: Feature[]): Data => ({ type: "FeatureCollection", features }) as Data;

function pointsFc(points: MapPoint[]) {
  return fc(
    points.map((p): Feature => ({
      type: "Feature",
      geometry: { type: "Point", coordinates: [p.lng, p.lat] },
      properties: { id: p.id, color: p.color, size: p.size ?? 6, ring: p.ring ?? "#ffffff" },
    }))
  );
}

function linesFc(lines: MapLine[]) {
  return fc(
    lines.map((l): Feature => ({
      type: "Feature",
      geometry: { type: "LineString", coordinates: l.path.map(([lat, lng]) => [lng, lat]) },
      properties: { color: l.color, width: l.width ?? 4, opacity: l.opacity ?? 0.85 },
    }))
  );
}

function areasFc(areas: MapArea[]) {
  return fc(
    areas.map((a): Feature => ({
      type: "Feature",
      geometry: { type: "Polygon", coordinates: [a.path.map(([lat, lng]) => [lng, lat])] },
      properties: { color: a.color },
    }))
  );
}

function heatFc(heat: MapHeat[]) {
  const max = Math.max(1, ...heat.map((h) => h.weight));
  return fc(
    heat.map((h): Feature => ({
      type: "Feature",
      geometry: { type: "Point", coordinates: [h.lng, h.lat] },
      properties: { w: h.weight / max },
    }))
  );
}

/** One MapLibre map on OpenStreetMap tiles: areas, heat, lines, then points on top. */
export function OsmMap({
  points = [],
  lines = [],
  areas = [],
  heat = [],
  fit = true,
  onPointClick,
  className,
  label,
}: Props) {
  const box = useRef<HTMLDivElement>(null);
  const map = useRef<MlMap | null>(null);
  const ready = useRef(false);
  const click = useRef(onPointClick);
  click.current = onPointClick;
  const latest = useRef({ points, lines, areas, heat });
  latest.current = { points, lines, areas, heat };

  useEffect(() => {
    if (!box.current) return;
    const m = new maplibregl.Map({
      container: box.current,
      center: GTA,
      zoom: 10,
      attributionControl: { compact: true },
      style: {
        version: 8,
        sources: {
          osm: {
            type: "raster",
            tiles: [TILE_URL],
            tileSize: 256,
            maxzoom: 19,
            attribution: "© OpenStreetMap contributors",
          },
        },
        layers: [{ id: "osm", type: "raster", source: "osm" }],
      },
    });
    m.addControl(new maplibregl.NavigationControl({ showCompass: false }), "top-right");
    m.on("load", () => {
      const { points: p, lines: l, areas: a, heat: h } = latest.current;
      m.addSource("areas", { type: "geojson", data: areasFc(a) });
      m.addSource("heat", { type: "geojson", data: heatFc(h) });
      m.addSource("lines", { type: "geojson", data: linesFc(l) });
      m.addSource("points", { type: "geojson", data: pointsFc(p) });
      m.addLayer({
        id: "areas-fill",
        type: "fill",
        source: "areas",
        paint: { "fill-color": ["get", "color"], "fill-opacity": 0.12 },
      });
      m.addLayer({
        id: "areas-line",
        type: "line",
        source: "areas",
        paint: { "line-color": ["get", "color"], "line-width": 2, "line-opacity": 0.7 },
      });
      m.addLayer({
        id: "heat",
        type: "heatmap",
        source: "heat",
        paint: { "heatmap-weight": ["get", "w"], "heatmap-radius": 28, "heatmap-opacity": 0.55 },
      });
      m.addLayer({
        id: "lines",
        type: "line",
        source: "lines",
        layout: { "line-cap": "round", "line-join": "round" },
        paint: {
          "line-color": ["get", "color"],
          "line-width": ["get", "width"],
          "line-opacity": ["get", "opacity"],
        },
      });
      m.addLayer({
        id: "points",
        type: "circle",
        source: "points",
        paint: {
          "circle-color": ["get", "color"],
          "circle-radius": ["get", "size"],
          "circle-stroke-color": ["get", "ring"],
          "circle-stroke-width": 2,
        },
      });
      m.on("click", "points", (e: MapLayerMouseEvent) => {
        const id = e.features?.[0]?.properties?.id;
        if (id && click.current) click.current(String(id));
      });
      m.on("mouseenter", "points", () => {
        m.getCanvas().style.cursor = "pointer";
      });
      m.on("mouseleave", "points", () => {
        m.getCanvas().style.cursor = "";
      });
      ready.current = true;
    });
    map.current = m;
    return () => {
      ready.current = false;
      m.remove();
      map.current = null;
    };
  }, []);

  useEffect(() => {
    const m = map.current;
    if (!m) return;
    const apply = () => {
      (m.getSource("points") as GeoJSONSource | undefined)?.setData(pointsFc(points));
      (m.getSource("lines") as GeoJSONSource | undefined)?.setData(linesFc(lines));
      (m.getSource("areas") as GeoJSONSource | undefined)?.setData(areasFc(areas));
      (m.getSource("heat") as GeoJSONSource | undefined)?.setData(heatFc(heat));
    };
    if (ready.current) apply();
    else m.once("load", apply);
  }, [points, lines, areas, heat]);

  const fitKey = points.length;
  useEffect(() => {
    const m = map.current;
    const pts = latest.current.points;
    if (!m || !fit || pts.length === 0) return;
    const go = () => {
      if (pts.length === 1) {
        m.jumpTo({ center: [pts[0].lng, pts[0].lat] as LngLatLike, zoom: 13 });
        return;
      }
      const b = new maplibregl.LngLatBounds();
      pts.forEach((p) => b.extend([p.lng, p.lat]));
      m.fitBounds(b, { padding: 56, maxZoom: 14, duration: 0 });
    };
    if (ready.current) go();
    else m.once("load", go);
  }, [fitKey, fit]);

  return (
    <div ref={box} role="region" aria-label={label} className={className ?? "h-full w-full"} />
  );
}
