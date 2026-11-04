/**
 * Proof media (photos + signatures) shared by driver web and mobile. Files go to
 * POST /v1/media/photo (multipart) and /v1/media/signature (PNG data URL); the returned
 * key is what POD, pickup docs, handover and safety reports send. Never invent local keys.
 */
export type Stroke = { x: number; y: number }[];
export type MediaRef = { key: string; content_type?: string; bytes?: number };

export const MAX_SIGNATURE_BYTES = 300_000;
export const MIN_SIGNATURE_POINTS = 8;

/** A signature counts once it has enough ink and spans a little width (stops a tap from passing). */
export function signatureReady(strokes: Stroke[]): boolean {
  const pts = strokes.flat();
  if (pts.length < MIN_SIGNATURE_POINTS) return false;
  const xs = pts.map((p) => p.x);
  return Math.max(...xs) - Math.min(...xs) >= 20;
}

export function isPngDataUrl(v: string): boolean {
  return (
    /^data:image\/png;base64,[A-Za-z0-9+/=]+$/.test(v) &&
    v.length * 0.75 <= MAX_SIGNATURE_BYTES + 64
  );
}

/** SVG path for a set of strokes; mobile draws with react-native-svg, web with canvas. */
export function strokesToPath(strokes: Stroke[]): string {
  return strokes
    .filter((s) => s.length)
    .map(
      (s) =>
        `M${s[0].x.toFixed(1)},${s[0].y.toFixed(1)}` +
        s
          .slice(1)
          .map((p) => ` L${p.x.toFixed(1)},${p.y.toFixed(1)}`)
          .join("")
    )
    .join(" ");
}

export type MediaPost = <T>(path: string, body: FormData | string) => Promise<T>;

export function mediaClient(post: MediaPost) {
  return {
    photo: (file: Blob, name = "photo.jpg") => {
      const fd = new FormData();
      fd.append("file", file, name);
      return post<MediaRef>("/v1/media/photo", fd);
    },
    /** Mobile: camera output is already a data URL (JPEG/PNG/WebP). */
    photoDataUrl: (dataUrl: string) =>
      post<MediaRef>("/v1/media/photo-data", JSON.stringify({ data_url: dataUrl })),
    signature: (dataUrl: string, signerName: string) => {
      if (!isPngDataUrl(dataUrl)) return Promise.reject(new Error("signature_invalid"));
      if (signerName.trim().length < 2) return Promise.reject(new Error("signer_name_required"));
      return post<MediaRef>(
        "/v1/media/signature",
        JSON.stringify({ data_url: dataUrl, signer_name: signerName.trim() })
      );
    },
  };
}

// --- Dependency-free PNG for mobile (no canvas/svg in the Expo app): rasterise strokes, stored-deflate PNG.
const CRC = (() => {
  const t = new Uint32Array(256);
  for (let n = 0; n < 256; n++) {
    let c = n;
    for (let k = 0; k < 8; k++) c = c & 1 ? 0xedb88320 ^ (c >>> 1) : c >>> 1;
    t[n] = c >>> 0;
  }
  return t;
})();
function crc32(b: Uint8Array): number {
  let c = 0xffffffff;
  for (const x of b) c = CRC[(c ^ x) & 0xff] ^ (c >>> 8);
  return (c ^ 0xffffffff) >>> 0;
}
const u32 = (n: number) => [(n >>> 24) & 255, (n >>> 16) & 255, (n >>> 8) & 255, n & 255];
function chunk(type: string, data: Uint8Array): number[] {
  const td = new Uint8Array(4 + data.length);
  for (let i = 0; i < 4; i++) td[i] = type.charCodeAt(i);
  td.set(data, 4);
  return [...u32(data.length), ...td, ...u32(crc32(td))];
}
function zlibStored(raw: Uint8Array): Uint8Array {
  const out: number[] = [0x78, 0x01];
  for (let i = 0; i < raw.length || i === 0; i += 65535) {
    const blk = raw.subarray(i, Math.min(i + 65535, raw.length));
    const last = i + 65535 >= raw.length ? 1 : 0;
    out.push(
      last,
      blk.length & 255,
      blk.length >>> 8,
      ~blk.length & 255,
      (~blk.length >>> 8) & 255
    );
    for (const x of blk) out.push(x);
    if (!raw.length) break;
  }
  let a = 1,
    b = 0;
  for (const x of raw) {
    a = (a + x) % 65521;
    b = (b + a) % 65521;
  }
  out.push(...u32(((b << 16) | a) >>> 0));
  return Uint8Array.from(out);
}
const B64 = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/";
function b64(bytes: Uint8Array): string {
  let s = "";
  for (let i = 0; i < bytes.length; i += 3) {
    const n = (bytes[i] << 16) | ((bytes[i + 1] ?? 0) << 8) | (bytes[i + 2] ?? 0);
    s +=
      B64[(n >>> 18) & 63] +
      B64[(n >>> 12) & 63] +
      (i + 1 < bytes.length ? B64[(n >>> 6) & 63] : "=") +
      (i + 2 < bytes.length ? B64[n & 63] : "=");
  }
  return s;
}

/** Strokes → black-on-white 8-bit greyscale PNG data URL (about 40 KB at 320×120). */
export function strokesToPngDataUrl(strokes: Stroke[], width = 320, height = 120, pen = 2): string {
  const W = Math.max(1, Math.round(width)),
    H = Math.max(1, Math.round(height));
  const px = new Uint8Array(W * H).fill(255);
  const dot = (x: number, y: number) => {
    for (let dy = -pen; dy <= pen; dy++)
      for (let dx = -pen; dx <= pen; dx++) {
        const X = Math.round(x + dx),
          Y = Math.round(y + dy);
        if (dx * dx + dy * dy <= pen * pen && X >= 0 && Y >= 0 && X < W && Y < H) px[Y * W + X] = 0;
      }
  };
  for (const s of strokes) {
    s.forEach((p, i) => {
      const q = s[i - 1] ?? p;
      const steps = Math.max(1, Math.ceil(Math.hypot(p.x - q.x, p.y - q.y)));
      for (let t = 0; t <= steps; t++)
        dot(q.x + ((p.x - q.x) * t) / steps, q.y + ((p.y - q.y) * t) / steps);
    });
  }
  const raw = new Uint8Array((W + 1) * H);
  for (let y = 0; y < H; y++) {
    raw[y * (W + 1)] = 0;
    raw.set(px.subarray(y * W, (y + 1) * W), y * (W + 1) + 1);
  }
  const ihdr = Uint8Array.from([...u32(W), ...u32(H), 8, 0, 0, 0, 0]);
  const png = Uint8Array.from([
    137,
    80,
    78,
    71,
    13,
    10,
    26,
    10,
    ...chunk("IHDR", ihdr),
    ...chunk("IDAT", zlibStored(raw)),
    ...chunk("IEND", new Uint8Array()),
  ]);
  return `data:image/png;base64,${b64(png)}`;
}
