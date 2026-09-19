"use client";

import { useState } from "react";
import { Download } from "lucide-react";
import { downloadOrderFile, podArtifactPath, podBundlePath } from "@/lib/orders";

/**
 * POD media is Fleetbase-hosted, so a browser cannot save it from the gallery:
 * the HTML `download` attribute is ignored cross-origin and the link just opens
 * the image. These buttons ask the API for the bytes instead (BR).
 */

type Common = {
  orderId: string;
  getApiToken: () => Promise<string>;
};

function useSave(getApiToken: () => Promise<string>) {
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function save(path: string, fallbackName: string) {
    setBusy(true);
    setError(null);
    try {
      await downloadOrderFile(await getApiToken(), path, fallbackName);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not download that file.");
    } finally {
      setBusy(false);
    }
  }

  return { busy, error, save };
}

export function PodDownloadAll({ orderId, getApiToken }: Common) {
  const { busy, error, save } = useSave(getApiToken);
  return (
    <div className="flex flex-wrap items-center gap-2">
      <button
        type="button"
        disabled={busy}
        onClick={() => void save(podBundlePath(orderId), "proof-of-delivery.zip")}
        className="inline-flex items-center gap-1.5 rounded-lg border border-primary/15 px-2.5 py-1 text-xs font-semibold text-secondary hover:bg-secondary/5 disabled:opacity-50"
      >
        <Download className="h-3.5 w-3.5" />
        {busy ? "Preparing…" : "Download all proof"}
      </button>
      {error ? <span className="text-xs text-red-600">{error}</span> : null}
    </div>
  );
}

export function PodDownloadOne({
  orderId,
  getApiToken,
  slug,
  fallbackName,
}: Common & { slug: unknown; fallbackName: string }) {
  const { busy, error, save } = useSave(getApiToken);
  const handle = typeof slug === "string" ? slug : "";
  if (!handle) return null;
  return (
    <div className="space-y-0.5">
      <button
        type="button"
        disabled={busy}
        onClick={() => void save(podArtifactPath(orderId, handle), fallbackName)}
        className="text-xs font-semibold text-secondary hover:underline disabled:opacity-50"
      >
        {busy ? "Saving…" : "Download"}
      </button>
      {error ? <p className="max-w-36 text-xs text-red-600">{error}</p> : null}
    </div>
  );
}
