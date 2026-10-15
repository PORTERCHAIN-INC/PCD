"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import {
  ACCEPT,
  STATUS_LABEL,
  customerAttachments,
  type CustomerAttachmentList,
} from "@/lib/attachments";

export function BookingDocuments({
  trackingNumber,
  getToken,
}: {
  trackingNumber: string;
  getToken: () => Promise<string | null>;
}) {
  const [data, setData] = useState<CustomerAttachmentList | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const pick = useRef<HTMLInputElement>(null);
  const cam = useRef<HTMLInputElement>(null);

  const load = useCallback(async () => {
    const t = await getToken();
    if (!t) return;
    try {
      setData(await customerAttachments.list(t, trackingNumber));
    } catch {
      /* not this customer's booking or offline */
    }
  }, [getToken, trackingNumber]);
  useEffect(() => {
    void load();
  }, [load]);

  async function add(file?: File) {
    const t = await getToken();
    if (!file || !t) return;
    setBusy(true);
    setError(null);
    try {
      await customerAttachments.upload(t, trackingNumber, file, true);
      await load();
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  }

  if (!data) return null;
  const canAdd = data.editable.pickup || data.editable.dropoff;
  if (!canAdd && data.items.length === 0) return null;
  return (
    <div className="mt-4 rounded-2xl bg-primary/[0.03] p-4 text-sm" data-testid="booking-documents">
      <p className="font-bold text-primary">Documents for the driver</p>
      <p className="text-primary/65">Only your assigned driver can open these.</p>
      <ul className="mt-2 space-y-1">
        {data.items.map((a) => (
          <li key={a.id} className="flex flex-wrap items-center gap-2">
            <button
              type="button"
              className="font-semibold text-secondary underline-offset-2 hover:underline"
              onClick={async () => {
                const t = await getToken();
                if (t)
                  await customerAttachments
                    .open(t, a.id)
                    .catch((e) => setError((e as Error).message));
              }}
            >
              {a.filename}
            </button>
            <span className="text-primary/65">
              {a.kind_label} · {a.stop === "pickup" ? "Pickup" : "Drop-off"}
            </span>
            <span className="rounded-full bg-white px-2 py-0.5 text-xs">
              {STATUS_LABEL[a.status]}
            </span>
            {data.editable[a.stop] && (
              <button
                type="button"
                className="text-xs text-red-600"
                onClick={async () => {
                  const t = await getToken();
                  if (t && window.confirm("Remove this document?")) {
                    await customerAttachments.remove(t, a.id);
                    await load();
                  }
                }}
              >
                Remove
              </button>
            )}
          </li>
        ))}
      </ul>
      {canAdd && (
        <div className="mt-3 flex gap-2">
          <button
            type="button"
            disabled={busy}
            className="rounded-full bg-primary px-4 py-2 font-semibold text-white"
            onClick={() => pick.current?.click()}
          >
            {busy ? "Uploading…" : "Attach document"}
          </button>
          <button
            type="button"
            disabled={busy}
            className="rounded-full border border-primary/20 px-4 py-2 font-semibold"
            onClick={() => cam.current?.click()}
          >
            Take photo
          </button>
          <input
            ref={pick}
            type="file"
            accept={ACCEPT}
            hidden
            onChange={(e) => void add(e.target.files?.[0])}
          />
          <input
            ref={cam}
            type="file"
            accept="image/*"
            capture="environment"
            hidden
            onChange={(e) => void add(e.target.files?.[0])}
          />
        </div>
      )}
      {error && <p className="mt-2 text-red-600">{error}</p>}
    </div>
  );
}
