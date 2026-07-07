"use client";

import { useMemo, useState } from "react";
import { View, Text, Pressable, StyleSheet } from "react-native";
import type { ReplayFrame } from "../session";
import { replayToLatLng } from "../geo";

export function RouteReplayControls({
  frames,
  onIndexChange,
}: {
  frames: ReplayFrame[];
  onIndexChange?: (index: number | null) => void;
}) {
  const [index, setIndex] = useState<number | null>(null);

  const replayPoint = useMemo(() => {
    if (index == null || !frames[index]) return null;
    return { latitude: frames[index].lat, longitude: frames[index].lng };
  }, [frames, index]);

  if (frames.length < 2) return null;

  function set(i: number | null) {
    setIndex(i);
    onIndexChange?.(i);
  }

  return (
    <View style={styles.wrap}>
      <Text style={styles.label}>Route replay ({frames.length} pts)</Text>
      <View style={styles.row}>
        <Pressable style={styles.btn} onPress={() => set(0)}>
          <Text style={styles.btnText}>Start</Text>
        </Pressable>
        <Pressable
          style={styles.btn}
          onPress={() => set(index == null ? 0 : Math.min(index + 1, frames.length - 1))}
        >
          <Text style={styles.btnText}>Step</Text>
        </Pressable>
        <Pressable style={styles.btn} onPress={() => set(frames.length - 1)}>
          <Text style={styles.btnText}>End</Text>
        </Pressable>
        <Pressable style={styles.btn} onPress={() => set(null)}>
          <Text style={styles.btnText}>Live</Text>
        </Pressable>
      </View>
      {index != null && frames[index]?.at ? (
        <Text style={styles.time}>{frames[index].at}</Text>
      ) : null}
      {replayPoint ? <Text style={styles.time}>Frame {index}</Text> : null}
    </View>
  );
}

export function replayMarkerCoordinate(frames: ReplayFrame[], index: number | null) {
  if (index == null || !frames[index]) return null;
  const pts = replayToLatLng(frames);
  return pts[index] ?? null;
}

const styles = StyleSheet.create({
  wrap: {
    backgroundColor: "rgba(255,255,255,0.95)",
    borderRadius: 12,
    padding: 12,
    gap: 8,
  },
  label: { fontWeight: "600", fontSize: 13, color: "#0a1628" },
  row: { flexDirection: "row", gap: 8 },
  btn: {
    flex: 1,
    backgroundColor: "#f1f5f9",
    paddingVertical: 8,
    borderRadius: 8,
    alignItems: "center",
  },
  btnText: { fontSize: 12, fontWeight: "600", color: "#2563eb" },
  time: { fontSize: 11, color: "#64748b" },
});
