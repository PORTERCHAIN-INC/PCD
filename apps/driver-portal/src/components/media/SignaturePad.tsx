"use client";

import { useRef, useState } from "react";
import { signatureReady, type Stroke } from "@porterchain/driver-flows";
import { mediaApi } from "@/lib/api";

/** Finger/stylus signature → PNG → /v1/media/signature → key (POD, pickup docs, handover). */
export function SignaturePad({
  label = "Signature",
  signerLabel = "Signer name",
  onSaved,
}: {
  label?: string;
  signerLabel?: string;
  onSaved: (key: string | null, signer: string) => void;
}) {
  const ref = useRef<HTMLCanvasElement>(null);
  const strokes = useRef<Stroke[]>([]);
  const [signer, setSigner] = useState("");
  const [ready, setReady] = useState(false);
  const [state, setState] = useState<"idle" | "saving" | "saved" | "error">("idle");
  const pt = (e: React.PointerEvent<HTMLCanvasElement>) => {
    const r = e.currentTarget.getBoundingClientRect();
    return { x: e.clientX - r.left, y: e.clientY - r.top };
  };
  const draw = (e: React.PointerEvent<HTMLCanvasElement>) => {
    if (e.buttons === 0 && e.type === "pointermove") return;
    const c = ref.current?.getContext("2d");
    const p = pt(e);
    const cur = strokes.current[strokes.current.length - 1];
    if (c && cur?.length) {
      const last = cur[cur.length - 1];
      c.lineWidth = 2;
      c.lineCap = "round";
      c.strokeStyle = "#111";
      c.beginPath();
      c.moveTo(last.x, last.y);
      c.lineTo(p.x, p.y);
      c.stroke();
    }
    cur?.push(p);
    setReady(signatureReady(strokes.current));
  };
  const clear = () => {
    strokes.current = [];
    const c = ref.current;
    c?.getContext("2d")?.clearRect(0, 0, c.width, c.height);
    setReady(false);
    setState("idle");
    onSaved(null, signer);
  };
  const save = async () => {
    if (!ref.current) return;
    setState("saving");
    try {
      const { key } = await mediaApi.signature(ref.current.toDataURL("image/png"), signer.trim());
      setState("saved");
      onSaved(key, signer.trim());
    } catch {
      setState("error");
      onSaved(null, signer);
    }
  };
  return (
    <div className="space-y-1">
      <p className="text-sm font-semibold">{label}</p>
      <input
        aria-label={signerLabel}
        placeholder={signerLabel}
        value={signer}
        onChange={(e) => setSigner(e.target.value)}
        className="w-full rounded border px-2 py-1 text-sm"
      />
      <canvas
        ref={ref}
        width={320}
        height={120}
        aria-label={`${label} pad`}
        role="img"
        className="touch-none rounded border bg-white"
        onPointerDown={(e) => {
          e.currentTarget.setPointerCapture(e.pointerId);
          strokes.current.push([pt(e)]);
        }}
        onPointerMove={draw}
      />
      <div className="flex gap-2 text-sm">
        <button type="button" onClick={clear}>
          Clear
        </button>
        <button
          type="button"
          disabled={!ready || !signer.trim() || state === "saving"}
          onClick={save}
        >
          {state === "saved" ? "Saved ✓" : state === "saving" ? "Saving…" : "Save signature"}
        </button>
        {state === "error" && <span className="text-red-700">Upload failed, try again</span>}
      </div>
    </div>
  );
}

/** Camera/file photo → /v1/media/photo → key. */
export function PhotoField({
  label,
  onSaved,
}: {
  label: string;
  onSaved: (key: string | null) => void;
}) {
  const [state, setState] = useState<"idle" | "saving" | "saved" | "error">("idle");
  return (
    <label className="block text-sm">
      {label}{" "}
      <input
        type="file"
        accept="image/*"
        aria-label={label}
        onChange={async (e) => {
          const f = e.target.files?.[0];
          if (!f) return;
          setState("saving");
          try {
            const { key } = await mediaApi.photo(f, f.name);
            setState("saved");
            onSaved(key);
          } catch {
            setState("error");
            onSaved(null);
          }
        }}
      />
      {state === "saving" && " Uploading…"}
      {state === "saved" && " ✓"}
      {state === "error" && <span className="text-red-700"> Upload failed</span>}
    </label>
  );
}
