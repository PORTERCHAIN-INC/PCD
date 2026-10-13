/**
 * Swipe-to-confirm for critical, hard-to-undo actions (Delivered, Mark failed, Send SOS).
 * A drag of ≥ 85 % of the track confirms; letting go earlier springs back. Screen readers get
 * a plain button (double-tap confirms) because swiping isn't accessible.
 */
import { useEffect, useRef, useState } from "react";
import {
  AccessibilityInfo,
  ActivityIndicator,
  PanResponder,
  StyleSheet,
  Text,
  View,
} from "react-native";
import Animated, {
  useAnimatedStyle,
  useSharedValue,
  withSpring,
  withTiming,
} from "react-native-reanimated";
import { haptic } from "../haptics";
import { color, radius, target, type } from "./theme";

const KNOB = target.primary - 12;

export function SwipeConfirm({
  label,
  onConfirm,
  tone = "primary",
  disabled = false,
  busy = false,
  testID,
}: {
  label: string;
  onConfirm: () => void;
  tone?: "primary" | "danger";
  disabled?: boolean;
  busy?: boolean;
  testID?: string;
}) {
  const [width, setWidth] = useState(0);
  const [sr, setSr] = useState(false);
  const x = useSharedValue(0);
  const fired = useRef(false);
  const max = Math.max(0, width - KNOB - 12);
  useEffect(() => {
    void AccessibilityInfo.isScreenReaderEnabled().then(setSr);
  }, []);
  useEffect(() => {
    if (!busy) {
      x.value = withSpring(0);
      fired.current = false;
    }
  }, [busy, x]);
  const accent = tone === "danger" ? color.danger : color.primary;
  const ink = tone === "danger" ? color.onDanger : color.onPrimary;

  const maxRef = useRef(max);
  maxRef.current = max;
  const confirmRef = useRef(onConfirm);
  confirmRef.current = onConfirm;

  const pan = useRef(
    PanResponder.create({
      onStartShouldSetPanResponder: () => true,
      onMoveShouldSetPanResponderCapture: (_e, g) => Math.abs(g.dx) > 4,
      onPanResponderTerminationRequest: () => false,
      onPanResponderGrant: () => haptic.tap(),
      onPanResponderMove: (_e, g) => {
        x.value = Math.max(0, Math.min(maxRef.current, g.dx));
      },
      onPanResponderRelease: (_e, g) => {
        if (!fired.current && g.dx >= maxRef.current * 0.85 && maxRef.current > 0) {
          fired.current = true;
          x.value = withTiming(maxRef.current, { duration: 120 });
          haptic.success();
          confirmRef.current();
        } else {
          x.value = withSpring(0, { damping: 16 });
        }
      },
    })
  ).current;

  const knob = useAnimatedStyle(() => ({ transform: [{ translateX: x.value }] }));
  const fill = useAnimatedStyle(() => ({ width: x.value + KNOB + 6 }));
  const off = disabled || busy;

  return (
    <View
      accessible={sr}
      accessibilityRole="button"
      accessibilityLabel={`${label}. Double-tap to confirm.`}
      accessibilityState={{ disabled: off, busy }}
      onAccessibilityTap={() => !off && onConfirm()}
      onLayout={(e) => setWidth(e.nativeEvent.layout.width)}
      style={[styles.track, { borderColor: off ? color.border : accent }]}
      testID={testID}
    >
      <Animated.View
        style={[styles.fill, { backgroundColor: off ? color.disabled : accent }, fill]}
      />
      <Text
        style={[styles.label, { color: off ? color.onDisabled : color.ink }]}
        maxFontSizeMultiplier={1.3}
      >
        {busy ? "Saving…" : label}
      </Text>
      <Animated.View
        {...(off ? {} : pan.panHandlers)}
        style={[styles.knob, { backgroundColor: off ? color.disabled : accent }, knob]}
      >
        {busy ? (
          <ActivityIndicator color={ink} />
        ) : (
          <Text style={[styles.arrow, { color: ink }]}>››</Text>
        )}
      </Animated.View>
    </View>
  );
}

const styles = StyleSheet.create({
  track: {
    height: target.primary,
    borderRadius: radius.pill,
    borderWidth: 2,
    backgroundColor: color.surface,
    justifyContent: "center",
    overflow: "hidden",
  },
  fill: {
    position: "absolute",
    left: 0,
    top: 0,
    bottom: 0,
    borderRadius: radius.pill,
    opacity: 0.22,
  },
  label: { ...type.button, textAlign: "center", paddingLeft: KNOB },
  knob: {
    position: "absolute",
    left: 4,
    width: KNOB,
    height: KNOB,
    borderRadius: KNOB / 2,
    alignItems: "center",
    justifyContent: "center",
  },
  arrow: { fontSize: 28, fontWeight: "900", marginTop: -3 },
});
