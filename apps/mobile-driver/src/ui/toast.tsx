/**
 * Slim toast at the top (under the status bar). Never covers the action area; auto-hides;
 * one at a time, newest wins. Call `toast.show(...)` from anywhere.
 */
import { useEffect, useState } from "react";
import { Pressable, StyleSheet, Text, View } from "react-native";
import Animated, { FadeInUp, FadeOutUp, ReduceMotion } from "react-native-reanimated";
import { useSafeAreaInsets } from "react-native-safe-area-context";
import { haptic } from "../haptics";
import { color, radius, space, type } from "./theme";

export type ToastTone = "info" | "success" | "warn" | "danger";
type Toast = { id: number; tone: ToastTone; title: string; body?: string };

let next = 1;
const listeners = new Set<(t: Toast | null) => void>();

export const toast = {
  show(tone: ToastTone, title: string, body?: string) {
    const t = { id: next++, tone, title, body };
    if (tone === "danger") haptic.error();
    else if (tone === "warn") haptic.warn();
    else if (tone === "success") haptic.success();
    listeners.forEach((l) => l(t));
  },
  clear() {
    listeners.forEach((l) => l(null));
  },
};

const INK: Record<ToastTone, string> = {
  info: color.infoInk,
  success: color.successInk,
  warn: color.warnInk,
  danger: color.danger,
};

export function ToastHost() {
  const insets = useSafeAreaInsets();
  const [t, setT] = useState<Toast | null>(null);
  useEffect(() => {
    const l = (x: Toast | null) => setT(x);
    listeners.add(l);
    return () => {
      listeners.delete(l);
    };
  }, []);
  useEffect(() => {
    if (!t) return;
    const timer = setTimeout(() => setT(null), t.tone === "danger" ? 6000 : 3500);
    return () => clearTimeout(timer);
  }, [t]);
  if (!t) return null;
  return (
    <View pointerEvents="box-none" style={[styles.wrap, { top: insets.top + space.sm }]}>
      <Animated.View
        key={t.id}
        entering={FadeInUp.duration(200).reduceMotion(ReduceMotion.System)}
        exiting={FadeOutUp.duration(160).reduceMotion(ReduceMotion.System)}
      >
        <Pressable
          onPress={() => setT(null)}
          accessibilityRole="alert"
          accessibilityLiveRegion="assertive"
          style={[styles.toast, { borderLeftColor: INK[t.tone] }]}
          testID="toast"
        >
          <Text style={[styles.title, { color: INK[t.tone] }]} numberOfLines={2}>
            {t.title}
          </Text>
          {t.body ? (
            <Text style={styles.body} numberOfLines={2}>
              {t.body}
            </Text>
          ) : null}
        </Pressable>
      </Animated.View>
    </View>
  );
}

const styles = StyleSheet.create({
  wrap: {
    position: "absolute",
    left: space.md,
    right: space.md,
    zIndex: 100,
    alignItems: "stretch",
  },
  toast: {
    maxWidth: 560,
    width: "100%",
    alignSelf: "center",
    backgroundColor: color.surface2,
    borderRadius: radius.md,
    borderLeftWidth: 4,
    paddingVertical: space.sm + 2,
    paddingHorizontal: space.lg,
    shadowColor: "#000",
    shadowOpacity: 0.4,
    shadowRadius: 12,
    shadowOffset: { width: 0, height: 4 },
    elevation: 8,
  },
  title: { ...type.bodyStrong, fontSize: 16, lineHeight: 22 },
  body: { ...type.small, color: color.inkMuted },
});
