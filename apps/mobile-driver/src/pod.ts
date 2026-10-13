import * as ImagePicker from "expo-image-picker";
import { ImageManipulator, SaveFormat } from "expo-image-manipulator";

/** ~280KB raw JPEG ≈ ~370KB data-URL — keeps offline queue payloads bounded. */
export const MAX_DATA_URL_CHARS = 380_000;

/**
 * Shrink attempts, largest first. A 12 MP phone photo at quality 0.35 is often > 1 MB of
 * base64, which used to fail with "photo too large" and block the delivery. 1280 px at 0.55
 * is ~150–250 KB and still shows the parcel, door and house number clearly.
 */
export const POD_SHRINK_STEPS: Array<{ width: number; compress: number }> = [
  { width: 1280, compress: 0.55 },
  { width: 1024, compress: 0.45 },
  { width: 800, compress: 0.4 },
];

export function toDataUrl(base64: string, mime = "image/jpeg"): string {
  return `data:${mime};base64,${base64}`;
}

/** First data URL that fits; null when even the smallest step is too big. */
export async function shrinkToFit(
  render: (step: { width: number; compress: number }) => Promise<string | null | undefined>
): Promise<string | null> {
  for (const step of POD_SHRINK_STEPS) {
    const b64 = await render(step);
    if (!b64) continue;
    const url = toDataUrl(b64);
    if (url.length <= MAX_DATA_URL_CHARS) return url;
  }
  return null;
}

async function renderStep(uri: string, step: { width: number; compress: number }) {
  const ctx = ImageManipulator.manipulate(uri);
  ctx.resize({ width: step.width });
  const img = await ctx.renderAsync();
  const out = await img.saveAsync({
    compress: step.compress,
    format: SaveFormat.JPEG,
    base64: true,
  });
  return out.base64;
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

  const result = await ImagePicker.launchCameraAsync({
    mediaTypes: ["images"],
    quality: 0.7,
    exif: false, // no GPS/EXIF in the proof photo (PIPEDA: only what's needed)
  });
  if (result.canceled || !result.assets?.[0]) {
    throw new Error("photo_cancelled");
  }
  const url = await shrinkToFit((step) => renderStep(result.assets[0].uri, step));
  if (!url) throw new Error("photo_too_large");
  return url;
}
