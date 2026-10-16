import { useEffect, useMemo, useRef, useState } from "react";
import { Linking, Modal, Pressable, StyleSheet, Text, TextInput, View } from "react-native";
import { CameraView, useCameraPermissions, type BarcodeScanningResult } from "expo-camera";

import { makeDeduper, scanFeedback, type ScanOutcome } from "../scanFeedback";
import { Banner, Body, Button, Title } from "./kit";
import { color, radius, space, target } from "./theme";

type Props = {
  visible: boolean;
  onClose: () => void;
  /** Return the outcome so the scanner beeps/buzzes correctly. A void return counts as "ok". */
  onScan: (value: string) => Promise<ScanOutcome | void> | ScanOutcome | void;
  /** Keep the camera open for the next box (pickup/delivery of many parcels). */
  continuous?: boolean;
  title?: string;
  hint?: string;
  /** e.g. "2 of 5 scanned" — shown over the camera in continuous mode. */
  progress?: string;
};

/**
 * Camera label scanner (iPhone + Android via expo-camera). PorterChain labels are QR;
 * code128 is read for the printed tracking barcode. No hardware scanners.
 */
export function BarcodeScannerModal({
  visible,
  onClose,
  onScan,
  continuous = false,
  title = "Scan label",
  hint = "Point the camera at the PorterChain label.",
  progress,
}: Props) {
  const [permission, requestPermission] = useCameraPermissions();
  const [torch, setTorch] = useState(false);
  const [manual, setManual] = useState("");
  const [last, setLast] = useState<{ text: string; tone: "ok" | "warn" | "error" } | null>(null);
  const busy = useRef(false);
  const fresh = useMemo(() => makeDeduper(), [visible]); // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(() => {
    if (visible) {
      busy.current = false;
      setLast(null);
      setManual("");
    } else {
      setTorch(false);
    }
  }, [visible]);

  useEffect(() => {
    if (visible && permission && !permission.granted && permission.canAskAgain) {
      void requestPermission();
    }
  }, [visible, permission, requestPermission]);

  async function submit(raw: string) {
    const value = raw.trim();
    if (!value || busy.current || !fresh(value)) return;
    busy.current = true;
    let outcome: ScanOutcome = "ok";
    try {
      outcome = (await onScan(value)) || "ok";
    } catch {
      outcome = "error";
    }
    scanFeedback(outcome);
    setLast({
      text:
        outcome === "queued"
          ? "Saved offline · will sync"
          : outcome === "warn"
            ? "Check this box"
            : outcome === "error"
              ? "Not accepted"
              : "Scanned",
      tone: outcome === "warn" ? "warn" : outcome === "error" ? "error" : "ok",
    });
    busy.current = false;
    if (!continuous || outcome === "done") onClose();
  }

  const onBarcode = (r: BarcodeScanningResult) => void submit(r.data || "");

  return (
    <Modal visible={visible} animationType="slide" onRequestClose={onClose}>
      <View style={styles.wrap} testID="barcode-scanner">
        <Title>{title}</Title>
        <Body>{hint}</Body>
        {!permission?.granted ? (
          <>
            <Banner
              tone="warn"
              title="Camera is off"
              body="Allow camera access to scan labels, or type the code below."
            />
            {permission && !permission.canAskAgain ? (
              <Button label="Open Settings" onPress={() => void Linking.openSettings()} />
            ) : null}
          </>
        ) : (
          <View style={styles.cameraWrap}>
            <CameraView
              style={styles.camera}
              facing="back"
              enableTorch={torch}
              barcodeScannerSettings={{ barcodeTypes: ["qr", "code128"] }}
              onBarcodeScanned={onBarcode}
            />
            <View style={styles.overlay} pointerEvents="box-none">
              {progress ? <Text style={styles.chip}>{progress}</Text> : <View />}
              <Pressable
                accessibilityRole="button"
                accessibilityLabel={torch ? "Turn light off" : "Turn light on"}
                testID="scanner-torch"
                onPress={() => setTorch((t) => !t)}
                style={[styles.torch, torch && styles.torchOn]}
              >
                <Text style={styles.torchText}>{torch ? "Light on" : "Light"}</Text>
              </Pressable>
            </View>
            {last ? (
              <Text
                testID="scanner-last"
                style={[
                  styles.last,
                  last.tone === "warn" && styles.lastWarn,
                  last.tone === "error" && styles.lastError,
                ]}
              >
                {last.text}
              </Text>
            ) : null}
          </View>
        )}
        <View style={styles.manualRow}>
          <TextInput
            testID="scanner-manual"
            value={manual}
            onChangeText={setManual}
            placeholder="Label won't scan? Type the code"
            autoCapitalize="characters"
            autoCorrect={false}
            style={styles.input}
            onSubmitEditing={() => {
              void submit(manual);
              setManual("");
            }}
          />
        </View>
        <Button label={continuous ? "Done" : "Cancel"} onPress={onClose} />
      </View>
    </Modal>
  );
}

const styles = StyleSheet.create({
  wrap: {
    flex: 1,
    backgroundColor: color.surface,
    padding: space.lg,
    gap: space.md,
    paddingTop: space.xxl,
  },
  cameraWrap: { flex: 1, minHeight: 320, borderRadius: radius.lg, overflow: "hidden" },
  camera: { flex: 1 },
  overlay: {
    position: "absolute",
    top: space.md,
    left: space.md,
    right: space.md,
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "center",
  },
  chip: {
    backgroundColor: "rgba(0,0,0,0.6)",
    color: "#fff",
    paddingHorizontal: space.md,
    paddingVertical: space.xs,
    borderRadius: radius.lg,
    fontWeight: "600",
  },
  torch: {
    backgroundColor: "rgba(0,0,0,0.6)",
    paddingHorizontal: space.md,
    paddingVertical: space.sm,
    borderRadius: radius.lg,
    minHeight: 44,
    justifyContent: "center",
  },
  torchOn: { backgroundColor: "#f5b400" },
  torchText: { color: "#fff", fontWeight: "700" },
  last: {
    position: "absolute",
    bottom: space.md,
    alignSelf: "center",
    backgroundColor: "#1f8b4c",
    color: "#fff",
    paddingHorizontal: space.lg,
    paddingVertical: space.sm,
    borderRadius: radius.lg,
    fontWeight: "700",
    overflow: "hidden",
  },
  lastWarn: { backgroundColor: "#b26a00" },
  lastError: { backgroundColor: "#b3261e" },
  manualRow: { flexDirection: "row", gap: space.sm },
  input: {
    flex: 1,
    borderWidth: 1,
    borderColor: color.border,
    borderRadius: radius.md,
    paddingHorizontal: space.md,
    minHeight: target.min,
    color: color.ink,
    fontSize: 18,
  },
});
