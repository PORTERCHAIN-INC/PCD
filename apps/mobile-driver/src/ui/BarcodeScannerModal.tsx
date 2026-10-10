import { useEffect, useState } from "react";
import { Modal, StyleSheet, View } from "react-native";
import { CameraView, useCameraPermissions, type BarcodeScanningResult } from "expo-camera";
import { Banner, Body, Button, Title } from "./kit";
import { color, radius, space } from "./theme";

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
    if (visible && permission && !permission.granted && permission.canAskAgain) {
      void requestPermission();
    }
  }, [visible, permission, requestPermission]);

  function handleScan(result: BarcodeScanningResult) {
    const value = (result.data || "").trim();
    if (locked || !value) return;
    setLocked(true);
    onScan(value);
    onClose();
  }

  return (
    <Modal visible={visible} animationType="slide" onRequestClose={onClose}>
      <View style={styles.wrap} testID="barcode-scanner">
        <Title>Scan label</Title>
        <Body>Point the camera at the PorterChain label.</Body>
        {!permission?.granted ? (
          <Banner
            tone="warn"
            title="Camera is off"
            body="Allow camera access in Settings to scan."
          />
        ) : (
          <CameraView
            style={styles.camera}
            facing="back"
            barcodeScannerSettings={{ barcodeTypes: ["qr", "code128"] }}
            onBarcodeScanned={locked ? undefined : handleScan}
          />
        )}
        <Button label="Cancel" onPress={onClose} />
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
  camera: { flex: 1, borderRadius: radius.lg, overflow: "hidden", minHeight: 320 },
});
