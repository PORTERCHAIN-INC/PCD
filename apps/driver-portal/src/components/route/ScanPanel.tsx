"use client";

import { useEffect, useRef, useState } from "react";
import { Camera, Check, ScanLine } from "lucide-react";
import { cn } from "@/lib/utils";

type Box = { code: string; label: string; done: boolean; missing?: boolean };

type Detector = { detect: (src: HTMLVideoElement) => Promise<{ rawValue: string }[]> };
type DetectorCtor = new (opts: { formats: string[] }) => Detector;

/**
 * Scan-to-confirm: camera barcode/QR reading where the phone supports it (BarcodeDetector),
 * typed label code otherwise. Every box must be scanned (or reported missing) before the
 * primary action unlocks.
 */
export function ScanPanel({
  title,
  boxes,
  onScan,
  onMissing,
}: {
  title: string;
  boxes: Box[];
  onScan: (code: string) => Promise<void>;
  onMissing?: (code: string) => void;
}) {
  const [camera, setCamera] = useState(false);
  const [manual, setManual] = useState("");
  const [msg, setMsg] = useState<string | null>(null);
  const done = boxes.filter((b) => b.done || b.missing).length;

  const submit = async (raw: string) => {
    const code = raw.trim();
    if (!code) return;
    setMsg(null);
    try {
      await onScan(code);
      setManual("");
    } catch (e) {
      setMsg(e instanceof Error ? e.message.replaceAll("_", " ") : "Scan failed");
    }
  };

  return (
    <div className="mt-5">
      <div className="flex items-baseline justify-between">
        <p className="text-sm font-semibold text-slate-800">{title}</p>
        <p className="text-2xl font-black tabular-nums text-[#0a1628]" aria-live="polite">
          {done}
          <span className="text-slate-400">/{boxes.length}</span>
        </p>
      </div>
      {camera ? (
        <CameraScanner onCode={(c) => void submit(c)} onClose={() => setCamera(false)} />
      ) : null}
      <div className="mt-3 flex gap-2">
        <button
          type="button"
          onClick={() => setCamera((c) => !c)}
          className="flex h-14 flex-1 items-center justify-center gap-2 rounded-2xl border-2 border-[#0a1628] text-base font-bold text-[#0a1628]"
        >
          <ScanLine className="h-6 w-6" aria-hidden /> {camera ? "Stop camera" : "Scan label"}
        </button>
      </div>
      <form
        className="mt-2 flex gap-2"
        onSubmit={(e) => {
          e.preventDefault();
          void submit(manual);
        }}
      >
        <input
          value={manual}
          onChange={(e) => setManual(e.target.value)}
          aria-label="Label code"
          placeholder="Or type the label code"
          autoCapitalize="characters"
          className="h-12 min-w-0 flex-1 rounded-xl border border-slate-300 px-3 text-base text-slate-900"
        />
        <button
          type="submit"
          className="h-12 rounded-xl bg-slate-100 px-4 text-sm font-bold text-slate-800"
        >
          Add
        </button>
      </form>
      {msg ? (
        <p role="alert" className="mt-2 text-sm font-medium text-red-700">
          {msg}
        </p>
      ) : null}
      <ul className="mt-3 space-y-2">
        {boxes.map((b) => (
          <li
            key={b.code}
            className={cn(
              "flex min-h-12 items-center gap-3 rounded-2xl border px-4",
              b.done
                ? "border-[#0a1628] bg-[#0a1628] text-white"
                : b.missing
                  ? "border-amber-300 bg-amber-50 text-amber-900"
                  : "border-slate-200 text-slate-900"
            )}
          >
            <span
              className={cn(
                "flex h-7 w-7 shrink-0 items-center justify-center rounded-full border-2",
                b.done ? "border-[#38bdf8] bg-[#38bdf8]" : "border-slate-300"
              )}
            >
              {b.done ? <Check className="h-4 w-4 text-[#0a1628]" aria-hidden /> : null}
            </span>
            <span className="flex-1 text-base font-semibold">{b.label}</span>
            <span className={cn("font-mono text-xs", b.done ? "text-slate-300" : "text-slate-500")}>
              {b.code.slice(-6)}
            </span>
            {!b.done && !b.missing && onMissing ? (
              <button
                type="button"
                onClick={() => onMissing(b.code)}
                className="min-h-10 rounded-xl px-2 text-sm font-semibold text-amber-800"
              >
                Missing
              </button>
            ) : null}
            {b.missing ? <span className="text-sm font-semibold">Reported</span> : null}
          </li>
        ))}
      </ul>
    </div>
  );
}

function CameraScanner({
  onCode,
  onClose,
}: {
  onCode: (code: string) => void;
  onClose: () => void;
}) {
  const video = useRef<HTMLVideoElement>(null);
  const emit = useRef(onCode);
  emit.current = onCode;
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const Ctor = (globalThis as unknown as { BarcodeDetector?: DetectorCtor }).BarcodeDetector;
    if (!Ctor) {
      setError("This phone can't scan in the browser. Type the code below.");
      return;
    }
    const detector = new Ctor({
      formats: ["qr_code", "code_128", "code_39", "ean_13", "data_matrix"],
    });
    let stream: MediaStream | null = null;
    let stop = false;
    let last = "";
    (async () => {
      try {
        stream = await navigator.mediaDevices.getUserMedia({
          video: { facingMode: "environment" },
        });
        if (!video.current) return;
        video.current.srcObject = stream;
        await video.current.play();
        while (!stop && video.current) {
          const found = await detector.detect(video.current).catch(() => []);
          const code = found[0]?.rawValue;
          if (code && code !== last) {
            last = code;
            navigator.vibrate?.(60);
            emit.current(code);
          }
          await new Promise((r) => setTimeout(r, 250));
        }
      } catch {
        setError("Camera blocked. Allow camera access or type the code below.");
      }
    })();
    return () => {
      stop = true;
      stream?.getTracks().forEach((t) => t.stop());
    };
  }, []);

  return (
    <div className="mt-3 overflow-hidden rounded-2xl bg-black">
      {error ? (
        <p className="flex items-center gap-2 p-4 text-sm text-white">
          <Camera className="h-5 w-5 shrink-0" aria-hidden /> {error}
          <button
            type="button"
            onClick={onClose}
            className="ml-auto min-h-10 rounded-lg bg-white/10 px-3 font-semibold"
          >
            OK
          </button>
        </p>
      ) : (
        <video
          ref={video}
          muted
          playsInline
          className="aspect-[4/3] w-full object-cover"
          aria-label="Camera scanner"
        />
      )}
    </div>
  );
}
