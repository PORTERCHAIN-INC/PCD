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

/** Documents need fine print to stay legible: start bigger, still capped by MAX_DATA_URL_CHARS. */
export const DOC_SHRINK_STEPS: Array<{ width: number; compress: number }> = [
  { width: 1600, compress: 0.6 },
  { width: 1400, compress: 0.5 },
  { width: 1200, compress: 0.45 },
  { width: 1000, compress: 0.4 },
];

export function toDataUrl(base64: string, mime = "image/jpeg"): string {
  return `data:${mime};base64,${base64}`;
}

/** First data URL that fits; null when even the smallest step is too big. */
export async function shrinkToFit(
  render: (step: { width: number; compress: number }) => Promise<string | null | undefined>,
  steps: Array<{ width: number; compress: number }> = POD_SHRINK_STEPS
): Promise<string | null> {
  for (const step of steps) {
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

  // Local Beta on the iOS Simulator only (.env.beta): the simulator camera can't take a picture
  // and the iOS 27.1 simulator photo library crashes (L171), so QA picks an image from Files.
  // Never set in store builds.
  if (process.env.EXPO_PUBLIC_POD_LIBRARY_FALLBACK === "1") {
    const DocumentPicker = await import("expo-document-picker");
    const r = await DocumentPicker.getDocumentAsync({
      type: ["image/*"],
      copyToCacheDirectory: true,
    });
    if (r.canceled || !r.assets?.[0]) throw new Error("photo_cancelled");
    const picked = r.assets[0].uri;
    const u = await shrinkToFit((step) => renderStep(picked, step));
    if (!u) throw new Error("photo_too_large");
    return u;
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

/**
 * Licence / insurance / permit photo from the camera, the photo library, or Files (images).
 * Auto-compressed to fit the upload cap; no EXIF/GPS kept.
 */
export async function captureDocumentDataUrl(
  source: "camera" | "library" | "file"
): Promise<string> {
  let uri: string | undefined;
  if (source === "file") {
    const DocumentPicker = await import("expo-document-picker");
    const r = await DocumentPicker.getDocumentAsync({
      type: ["image/*"],
      copyToCacheDirectory: true,
    });
    if (r.canceled || !r.assets?.[0]) throw new Error("photo_cancelled");
    uri = r.assets[0].uri;
  } else if (source === "library") {
    uri = await pickFromLibrary({ mediaTypes: ["images"], quality: 0.8, exif: false });
  } else {
    let { status } = await ImagePicker.getCameraPermissionsAsync();
    if (status !== "granted") status = (await ImagePicker.requestCameraPermissionsAsync()).status;
    if (status !== "granted") throw new Error("camera_permission_denied");
    const r = await ImagePicker.launchCameraAsync({
      mediaTypes: ["images"],
      quality: 0.8,
      exif: false,
    });
    if (r.canceled || !r.assets?.[0]) throw new Error("photo_cancelled");
    uri = r.assets[0].uri;
  }
  const url = await shrinkToFit((step) => renderStep(uri as string, step), DOC_SHRINK_STEPS);
  if (!url) throw new Error("photo_too_large");
  return url;
}

/**
 * L171: the photo library can fail on some devices/simulators. Use the Files
 * picker when it throws (or when the build asks for it), never crash the flow.
 */
async function pickFromLibrary(opts: ImagePicker.ImagePickerOptions): Promise<string> {
  if (process.env.EXPO_PUBLIC_POD_LIBRARY_FALLBACK !== "1") {
    try {
      const r = await ImagePicker.launchImageLibraryAsync(opts);
      if (r.canceled || !r.assets?.[0]) throw new Error("photo_cancelled");
      return r.assets[0].uri;
    } catch (e) {
      if (e instanceof Error && e.message === "photo_cancelled") throw e;
    }
  }
  const DocumentPicker = await import("expo-document-picker");
  const d = await DocumentPicker.getDocumentAsync({
    type: ["image/*"],
    copyToCacheDirectory: true,
  });
  if (d.canceled || !d.assets?.[0]) throw new Error("photo_cancelled");
  return d.assets[0].uri;
}

/** Square profile photo (512 px, ~60 KB) from camera or library. No EXIF/GPS kept. */
export async function captureAvatarDataUrl(source: "camera" | "library"): Promise<string> {
  const opts = {
    mediaTypes: ["images"] as ImagePicker.MediaType[],
    quality: 0.8,
    exif: false,
    allowsEditing: true,
    aspect: [1, 1] as [number, number],
  };
  if (source === "camera") {
    let { status } = await ImagePicker.getCameraPermissionsAsync();
    if (status !== "granted") status = (await ImagePicker.requestCameraPermissionsAsync()).status;
    if (status !== "granted") throw new Error("camera_permission_denied");
  }
  let uri: string;
  if (source === "camera") {
    const r = await ImagePicker.launchCameraAsync(opts);
    if (r.canceled || !r.assets?.[0]) throw new Error("photo_cancelled");
    uri = r.assets[0].uri;
  } else {
    uri = await pickFromLibrary(opts);
  }
  const b64 = await renderStep(uri, { width: 512, compress: 0.8 });
  if (!b64) throw new Error("photo_failed");
  return toDataUrl(b64);
}
