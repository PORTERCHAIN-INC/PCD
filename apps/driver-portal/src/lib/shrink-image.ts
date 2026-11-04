/** L193/L194: phone photos are often 2–6 MB. Downscale + re-encode in the browser until under maxBytes. */
export async function shrinkImageToDataUrl(file: File, maxBytes = 250_000): Promise<string> {
  const readAsDataUrl = (blob: Blob) =>
    new Promise<string>((resolve, reject) => {
      const r = new FileReader();
      r.onload = () => resolve(String(r.result || ""));
      r.onerror = () => reject(r.error);
      r.readAsDataURL(blob);
    });
  if (file.size <= maxBytes) return readAsDataUrl(file);
  const bitmap = await createImageBitmap(file);
  let side = Math.min(2000, Math.max(bitmap.width, bitmap.height));
  for (let i = 0; i < 8; i++) {
    const scale = side / Math.max(bitmap.width, bitmap.height);
    const canvas = document.createElement("canvas");
    canvas.width = Math.max(1, Math.round(bitmap.width * scale));
    canvas.height = Math.max(1, Math.round(bitmap.height * scale));
    canvas.getContext("2d")?.drawImage(bitmap, 0, 0, canvas.width, canvas.height);
    for (const q of [0.82, 0.7, 0.6]) {
      const blob = await new Promise<Blob | null>((res) => canvas.toBlob(res, "image/jpeg", q));
      if (blob && blob.size <= maxBytes) return readAsDataUrl(blob);
    }
    side = Math.round(side * 0.75);
  }
  throw new Error("too_large");
}
