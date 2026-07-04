"use client";

import { Heatmap } from "react-native-maps";
import type { HeatmapPoint } from "../session";

export function HeatmapLayer({ points }: { points: HeatmapPoint[] }) {
  if (points.length < 2) return null;

  return (
    <Heatmap
      points={points.map((p) => ({
        latitude: p.lat,
        longitude: p.lng,
        weight: p.weight ?? 1,
      }))}
      radius={28}
      opacity={0.65}
      gradient={{
        colors: ["#3b82f622", "#2563eb55", "#dc262688"],
        startPoints: [0.1, 0.5, 1],
        colorMapSize: 256,
      }}
    />
  );
}
