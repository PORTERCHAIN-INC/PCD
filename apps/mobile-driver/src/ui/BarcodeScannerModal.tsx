import { useEffect, useState } from "react";
import { Modal, Text, View, StyleSheet } from "react-native";
import { CameraView, useCameraPermissions, type BarcodeScanningResult } from "expo-camera";
import { colors, radius, spacing, typography } from "@porterchain/mobile-theme";
import { PrimaryButton } from "./PrimaryButton";

type Props = {
  visible: boolean;
  onClose: () => void;
  onScan: (value: string) => void;
};

export function BarcodeScannerModal({ visible, onClose, onScan }: Props) {
  const [permission, requestPermission] = useCameraPermissions();
  const [locked, setLocked] = useState(false);

  useEffect(() => {
    if (visible) setLocked(false);
  }, [visible]);

  useEffect(() => {
    if (visible && permission && !permission.granted) {
      void requestPermission();
    }
  }, [visible, permission, requestPermission]);

  function handleScan(result: BarcodeScanningResult) {
    if (locked) return;
    const value = (result.data || "").trim();
    if (!value) return;
    setLocked(true);
    onScan(value);
    onClose();
  }

  return (
    <Modal visible={visible} animationType="slide" onRequestClose={onClose}>
      <View style={styles.wrap} testID="barcode-scanner">
        <Text style={styles.title}>Scan barcode</Text>
        <Text style={styles.lede}>Point at PorterChain label QR or Code128. First read wins.</Text>
        {!permission?.granted ? (
          <Text style={styles.warn}>Camera permission required for scanning.</Text>
        ) : (
          <CameraView
            style={styles.camera}
            facing="back"
            barcodeScannerSettings={{
              barcodeTypes: ["qr", "code128"],
            }}
            onBarcodeScanned={locked ? undefined : handleScan}
          />
        )}
        <PrimaryButton tone="ghost" label="Cancel" onPress={onClose} />
      </View>
    </Modal>
  );
}

const styles = StyleSheet.create({
  wrap: {
    flex: 1,
    backgroundColor: colors.white,
    padding: spacing.lg,
    gap: spacing.md,
    paddingTop: spacing.xl,
  },
  title: { ...typography.title, fontSize: 24, color: colors.primary },
  lede: { ...typography.caption, color: colors.muted },
  warn: { ...typography.caption, color: colors.danger, fontWeight: "600" },
  camera: {
    flex: 1,
    borderRadius: radius.xl,
    overflow: "hidden",
    minHeight: 320,
  },
});
