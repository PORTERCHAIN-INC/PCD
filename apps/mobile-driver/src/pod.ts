import * as ImagePicker from "expo-image-picker";

/** ~280KB raw JPEG ≈ ~370KB data-URL — keeps offline queue payloads bounded. */
const MAX_DATA_URL_CHARS = 380_000;

async function assetToDataUrl(asset: ImagePicker.ImagePickerAsset): Promise<string> {
  if (!asset.base64) throw new Error("photo_encode_failed");
  const mime = asset.mimeType ?? "image/jpeg";
  const dataUrl = `data:${mime};base64,${asset.base64}`;
  if (dataUrl.length > MAX_DATA_URL_CHARS) {
    throw new Error("photo_too_large");
  }
  return dataUrl;
}

export async function capturePodPhotoDataUrl(): Promise<string> {
  const existing = await ImagePicker.getCameraPermissionsAsync();
  let status = existing.status;
  if (status !== "granted") {
    const asked = await ImagePicker.requestCameraPermissionsAsync();
    status = asked.status;
  }
  if (status !== "granted") {
    throw new Error("camera_permission_denied");
  }

  // Compress at capture: lower quality + no EXIF to shrink offline POD queue risk.
  const result = await ImagePicker.launchCameraAsync({
    mediaTypes: ["images"],
    quality: 0.35,
    base64: true,
    exif: false,
  });
  if (result.canceled || !result.assets?.[0]) {
    throw new Error("photo_cancelled");
  }
  return assetToDataUrl(result.assets[0]);
}

export async function pickDocumentPhotoDataUrl(): Promise<string> {
  const existing = await ImagePicker.getMediaLibraryPermissionsAsync();
  let status = existing.status;
  if (status !== "granted") {
    const asked = await ImagePicker.requestMediaLibraryPermissionsAsync();
    status = asked.status;
  }
  if (status !== "granted") {
    return capturePodPhotoDataUrl();
  }

  const result = await ImagePicker.launchImageLibraryAsync({
    mediaTypes: ["images"],
    quality: 0.4,
    base64: true,
    exif: false,
  });
  if (result.canceled || !result.assets?.[0]) {
    throw new Error("photo_cancelled");
  }
  return assetToDataUrl(result.assets[0]);
}
