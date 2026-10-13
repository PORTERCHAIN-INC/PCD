/**
 * Drive mode: a dashboard-mount view you can read in one glance. Huge ETA + street, one giant
 * Navigate button, screen kept awake, next stop read out loud (phone TTS, free/offline).
 * Landscape: ETA on the left, actions on the right.
 */
import { useEffect, useState } from "react";
import { Modal, StyleSheet, Text, View } from "react-native";
import { SafeAreaProvider, useSafeAreaInsets } from "react-native-safe-area-context";
import { KIND_LABEL, type DispatchStop } from "../dispatchRoute";
import { haptic } from "../haptics";
import { distanceLabel } from "../smart/geo";
import { speak, stopReadout, stopSpeaking } from "../smart/voice";
import { Button } from "./kit";
import { useLayout } from "./layout";
import { PressScale } from "./motion";
import { color, radius, space, type } from "./theme";

type Props = {
  stop: DispatchStop;
  index: number;
  total: number;
  eta: string | null;
  etaMin: number | null;
  distance: number | null;
  saver: boolean;
  onNavigate: () => void;
  onArrived: () => void;
  onClose: () => void;
};

export function DriveMode(p: Props) {
  return (
    <Modal
      visible
      animationType="fade"
      presentationStyle="fullScreen"
      statusBarTranslucent
      onRequestClose={p.onClose}
    >
      <SafeAreaProvider>
        <DriveBody {...p} />
      </SafeAreaProvider>
    </Modal>
  );
}

export function DriveBody(p: Props) {
  const insets = useSafeAreaInsets();
  const L = useLayout();
  const [voice, setVoice] = useState(true);

  useEffect(() => {
    let release: (() => void) | null = null;
    void import("expo-keep-awake")
      .then((K) =>
        K.activateKeepAwakeAsync("drive-mode").then(
          () => (release = () => void K.deactivateKeepAwake("drive-mode"))
        )
      )
      .catch(() => undefined);
    return () => release?.();
  }, []);

  const key = p.stop.keys.join(",");
  useEffect(() => {
    if (voice) void speak(stopReadout(p.stop, p.etaMin));
    return () => void stopSpeaking();
  }, [key, voice]); // eslint-disable-line react-hooks/exhaustive-deps

  const near = p.distance != null && p.distance < 300;
  const info = (
    <View style={[styles.info, L.landscape && styles.flex]}>
      <Text style={styles.kicker}>
        {p.index}/{p.total} · {KIND_LABEL[p.stop.kind]}
        {p.saver ? " · battery saver" : ""}
      </Text>
      <Text style={styles.eta} adjustsFontSizeToFit numberOfLines={1} testID="drive-eta">
        {p.eta ?? (near ? "Here" : "—")}
      </Text>
      {p.distance != null ? <Text style={styles.dist}>{distanceLabel(p.distance)}</Text> : null}
      <Text style={styles.addr} numberOfLines={L.landscape ? 2 : 3} maxFontSizeMultiplier={1.3}>
        {p.stop.address ?? "Address on file"}
      </Text>
      {p.stop.liftgate ? <Text style={styles.warn}>⚠ Liftgate</Text> : null}
    </View>
  );
  const actions = (
    <View style={[styles.actions, L.landscape && styles.actionsSide]}>
      {near ? (
        <Button tone="primary" label="I'm here" onPress={p.onArrived} testID="drive-arrived" />
      ) : (
        <Button tone="primary" label="Navigate" onPress={p.onNavigate} testID="drive-navigate" />
      )}
      <View style={styles.row}>
        <Pill
          label={voice ? "Voice on" : "Voice off"}
          on={voice}
          onPress={() => {
            haptic.tap();
            setVoice((v) => !v);
          }}
        />
        <Pill label="Repeat" onPress={() => void speak(stopReadout(p.stop, p.etaMin))} />
        <Pill label="Exit" onPress={p.onClose} testID="drive-exit" />
      </View>
    </View>
  );
  return (
    <View
      style={[
        styles.page,
        L.landscape && styles.pageRow,
        {
          paddingTop: insets.top + space.lg,
          paddingBottom: Math.max(insets.bottom, space.lg),
          paddingLeft: insets.left + L.gutter,
          paddingRight: insets.right + L.gutter,
        },
      ]}
      testID="drive-mode"
    >
      {info}
      {actions}
    </View>
  );
}

function Pill({
  label,
  onPress,
  on,
  testID,
}: {
  label: string;
  onPress: () => void;
  on?: boolean;
  testID?: string;
}) {
  return (
    <PressScale
      accessibilityRole="button"
      onPress={onPress}
      style={[styles.pill, on && styles.pillOn]}
      testID={testID}
    >
      <Text style={[styles.pillText, on && styles.pillTextOn]}>{label}</Text>
    </PressScale>
  );
}

const styles = StyleSheet.create({
  page: { flex: 1, backgroundColor: "#03070F", justifyContent: "space-between", gap: space.xl },
  pageRow: { flexDirection: "row", alignItems: "center" },
  flex: { flex: 1 },
  info: { gap: space.sm },
  kicker: { ...type.label, color: color.primary },
  eta: {
    fontSize: 104,
    lineHeight: 112,
    fontWeight: "900",
    color: color.ink,
    fontVariant: ["tabular-nums"],
    letterSpacing: -3,
  },
  dist: { ...type.display, color: color.inkMuted },
  addr: { fontSize: 30, lineHeight: 36, fontWeight: "800", color: color.ink },
  warn: { ...type.bodyStrong, color: color.warnInk },
  actions: { gap: space.md },
  actionsSide: { width: "42%" },
  row: { flexDirection: "row", gap: space.sm },
  pill: {
    flex: 1,
    minHeight: 52,
    borderRadius: radius.pill,
    borderWidth: 1,
    borderColor: color.border,
    alignItems: "center",
    justifyContent: "center",
  },
  pillOn: { borderColor: color.primary },
  pillText: { ...type.small, fontWeight: "800", color: color.inkMuted },
  pillTextOn: { color: color.primary },
});
