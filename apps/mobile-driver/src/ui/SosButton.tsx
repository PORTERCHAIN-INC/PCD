/**
 * SOS: hold the button 1.2 s (can't fire from a pocket) → full-screen red page with
 * "Call 911" and swipe-to-send. Dispatch gets the live location.
 */
import { useState } from "react";
import { Linking, StyleSheet, Text } from "react-native";
import { haptic } from "../haptics";
import { sendSos } from "../sos";
import { Body, Button } from "./kit";
import { PressScale } from "./motion";
import { Sheet } from "./Sheet";
import { SwipeConfirm } from "./SwipeConfirm";
import { color, radius, target, type } from "./theme";
import { toast } from "./toast";

export function useSos() {
  const [state, setState] = useState<"idle" | "sending" | "sent" | "failed">("idle");
  const [open, setOpen] = useState(false);
  const ask = () => {
    haptic.heavy();
    setOpen(true);
  };
  const send = () => {
    setState("sending");
    void sendSos()
      .then(() => {
        haptic.success();
        setState("sent");
        setOpen(false);
        toast.show("success", "SOS sent", "Dispatch has your location and will call you.");
      })
      .catch(() => {
        haptic.error();
        setState("failed");
      });
  };
  const page = (
    <Sheet
      visible={open}
      tone="danger"
      kicker="Emergency"
      title="Send SOS to dispatch?"
      onClose={() => setOpen(false)}
      testID="page-sos"
      footer={
        <>
          <SwipeConfirm
            tone="danger"
            label="Swipe to send SOS"
            busy={state === "sending"}
            onConfirm={send}
            testID="sos-confirm"
          />
          <Button
            tone="danger"
            label="Call 911"
            onPress={() => void Linking.openURL("tel:911")}
            testID="sos-911"
          />
        </>
      }
    >
      <Body>Dispatch gets your live location and calls you right away.</Body>
      <Body>In immediate danger, call 911 first.</Body>
      {state === "failed" ? (
        <Text style={styles.fail} accessibilityRole="alert">
          SOS did not send. No connection: call 911 or dispatch.
        </Text>
      ) : null}
    </Sheet>
  );
  return { state, ask, page };
}

export function SosButton({ onAsk }: { onAsk: () => void }) {
  return (
    <PressScale
      accessibilityRole="button"
      accessibilityLabel="SOS. Press and hold to contact dispatch in an emergency"
      hitSlop={8}
      delayLongPress={1200}
      onLongPress={onAsk}
      onPress={() => toast.show("info", "Hold SOS for a second", "So it can't go off by accident.")}
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
  fail: { ...type.bodyStrong, color: color.danger },
});
