/** Hold-to-send SOS (1.2 s) so it can't fire from a pocket; then a final confirm with 911. */
import { useState } from "react";
import { Alert, Linking, StyleSheet, Text } from "react-native";
import { haptic } from "../haptics";
import { sendSos } from "../sos";
import { PressScale } from "./motion";
import { color, radius, target, type } from "./theme";

export function useSos() {
  const [state, setState] = useState<"idle" | "sending" | "sent" | "failed">("idle");
  const ask = () => {
    haptic.heavy();
    Alert.alert(
      "Send SOS to dispatch?",
      "Dispatch gets your location and calls you. In immediate danger, call 911.",
      [
        { text: "Cancel", style: "cancel" },
        { text: "Call 911", onPress: () => void Linking.openURL("tel:911") },
        {
          text: "Send SOS",
          style: "destructive",
          onPress: () => {
            setState("sending");
            void sendSos()
              .then(() => {
                haptic.success();
                setState("sent");
              })
              .catch(() => {
                haptic.error();
                setState("failed");
              });
          },
        },
      ]
    );
  };
  return { state, ask };
}

export function SosButton({ onAsk }: { onAsk: () => void }) {
  return (
    <PressScale
      accessibilityRole="button"
      accessibilityLabel="SOS. Press and hold to contact dispatch in an emergency"
      hitSlop={8}
      delayLongPress={1200}
      onLongPress={onAsk}
      onPress={() => {
        haptic.tap();
        Alert.alert("SOS", "Press and hold SOS to contact dispatch.");
      }}
      style={styles.sos}
      testID="sos-hold"
    >
      <Text style={styles.text}>SOS</Text>
    </PressScale>
  );
}

const styles = StyleSheet.create({
  sos: {
    minWidth: target.min,
    height: 52,
    borderRadius: radius.pill,
    borderWidth: 2,
    borderColor: color.danger,
    alignItems: "center",
    justifyContent: "center",
    paddingHorizontal: 14,
  },
  text: { ...type.label, color: color.danger, fontSize: 15 },
});
