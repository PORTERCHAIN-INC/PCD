import { useState } from "react";
import { ScrollView } from "react-native";
import { useRoute } from "@react-navigation/native";
import type { RouteProp } from "@react-navigation/native";
import * as ImagePicker from "expo-image-picker";
import { DRIVER_OFFLINE_ACTIONS } from "@porterchain/mobile-api";
import { useOfflineSync } from "@porterchain/mobile-offline";
import { OptimizedImage } from "@porterchain/mobile-performance";
import { useTheme } from "@porterchain/mobile-theme";
import { Body, Button, Input, Screen, SuccessState } from "@porterchain/mobile-ui";
import { useDriverApi } from "../../api/DriverApiContext";
import { ScreenHeader } from "../../components/ScreenHeader";
import type { JobsStackParamList } from "../../navigation/types";

export function PodScreen() {
  const { theme } = useTheme();
  const api = useDriverApi();
  const { runDirectOrQueue } = useOfflineSync();
  const route = useRoute<RouteProp<JobsStackParamList, "Pod">>();
  const { orderId, routeId, stopId } = route.params;

  const [otp, setOtp] = useState("");
  const [signature, setSignature] = useState("");
  const [photoUrl, setPhotoUrl] = useState("");
  const [done, setDone] = useState(false);
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState<string | null>(null);

  async function run(
    actionType: string,
    payload: Record<string, unknown>,
    onlineExecute?: () => Promise<unknown>,
    localUri?: string
  ) {
    setLoading(true);
    setMessage(null);
    try {
      const result = await runDirectOrQueue(actionType, payload, onlineExecute, localUri);
      setMessage(result.mode === "queued" ? "Saved offline — will sync when connected." : "Synced via Porterchain API.");
    } catch (e) {
      setMessage(e instanceof Error ? e.message : "Failed");
    } finally {
      setLoading(false);
    }
  }

  async function complete() {
    await run(
      DRIVER_OFFLINE_ACTIONS.POD_COMPLETE,
      { route_id: routeId, stop_id: stopId, otp },
      () => api.podComplete(routeId, stopId, otp)
    );
    setDone(true);
  }

  async function capturePhoto(source: "camera" | "library") {
    const permission =
      source === "camera"
        ? await ImagePicker.requestCameraPermissionsAsync()
        : await ImagePicker.requestMediaLibraryPermissionsAsync();
    if (!permission.granted) {
      setMessage("Camera or photo library permission is required.");
      return;
    }

    const result =
      source === "camera"
        ? await ImagePicker.launchCameraAsync({ quality: 0.7, allowsEditing: true })
        : await ImagePicker.launchImageLibraryAsync({ quality: 0.7, allowsEditing: true });

    if (!result.canceled && result.assets[0]?.uri) {
      setPhotoUrl(result.assets[0].uri);
    }
  }

  return (
    <Screen>
      <ScreenHeader title="Proof of delivery" subtitle={orderId} />
      {done ? (
        <SuccessState title="POD captured" message="Delivery recorded through Porterchain API." />
      ) : (
        <ScrollView contentContainerStyle={{ padding: theme.spacing.lg, gap: theme.spacing.md }}>
          <Button
            label="Generate OTP"
            variant="secondary"
            onPress={() =>
              void run(
                DRIVER_OFFLINE_ACTIONS.GENERATE_OTP,
                { order_id: orderId },
                () => api.generateOtp(orderId)
              )
            }
          />
          <Input label="OTP" value={otp} onChangeText={setOtp} keyboardType="number-pad" />
          <Button
            label="Verify OTP"
            variant="ghost"
            onPress={() =>
              void run(DRIVER_OFFLINE_ACTIONS.OTP_VERIFY, { order_id: orderId, otp })
            }
          />
          <Input label="Signature (base64/text)" value={signature} onChangeText={setSignature} multiline />
          <Button
            label="Upload signature"
            variant="secondary"
            onPress={() =>
              void run(
                DRIVER_OFFLINE_ACTIONS.POD_SIGNATURE,
                { route_id: routeId, stop_id: stopId, signature_data: signature },
                () => api.podSignature(routeId, stopId, signature)
              )
            }
          />
          <View style={{ flexDirection: "row", gap: theme.spacing.sm }}>
            <Button label="Take photo" variant="secondary" style={{ flex: 1 }} onPress={() => void capturePhoto("camera")} />
            <Button label="Choose photo" variant="outline" style={{ flex: 1 }} onPress={() => void capturePhoto("library")} />
          </View>
          {photoUrl ? (
            <OptimizedImage
              source={{ uri: photoUrl }}
              style={{ width: "100%", height: 180, borderRadius: theme.radii.md }}
              contentFit="cover"
            />
          ) : null}
          <Button
            label="Upload photo"
            variant="secondary"
            onPress={() =>
              void run(
                DRIVER_OFFLINE_ACTIONS.POD_PHOTO,
                { route_id: routeId, stop_id: stopId, file_url: photoUrl },
                () => api.podPhoto(routeId, stopId, photoUrl),
                photoUrl
              )
            }
          />
          {message ? <Body muted>{message}</Body> : null}
          <Button label="Complete delivery" loading={loading} fullWidth onPress={() => void complete()} />
        </ScrollView>
      )}
    </Screen>
  );
}
