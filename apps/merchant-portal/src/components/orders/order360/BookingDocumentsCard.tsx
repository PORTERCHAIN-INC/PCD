"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import Button from "@/components/ui/Button";
import {
  ACCEPT,
  attachmentsApi,
  type AttachmentList,
  type BookingAttachment,
} from "@/lib/attachments";
import { Card } from "./shared";

const STATUS: Record<BookingAttachment["status"], { label: string; cls: string }> = {
  waiting: { label: "Not opened yet", cls: "bg-gray-100 text-gray-700" },
  viewed_by_driver: { label: "Viewed by driver", cls: "bg-blue-100 text-blue-800" },
  shown_at_pickup: { label: "Shown at pickup", cls: "bg-green-100 text-green-800" },
};

type Pending = {
  file: File;
  preview: string | null;
  kind: string;
  stop: "pickup" | "dropoff";
  required: boolean;
  save: boolean;
  note: string;
};

export function BookingDocumentsCard({
  orderId,
  getApiToken,
  orgId,
  canWrite,
}: {
  orderId: string;
  getApiToken?: () => Promise<string>;
  orgId?: string;
  canWrite: boolean;
}) {
  const [data, setData] = useState<AttachmentList | null>(null);
  const [pending, setPending] = useState<Pending | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [drag, setDrag] = useState(false);
  const pickRef = useRef<HTMLInputElement>(null);
  const camRef = useRef<HTMLInputElement>(null);

  const load = useCallback(async () => {
    if (!getApiToken) return;
    try {
      setData(await attachmentsApi.list(await getApiToken(), orderId, orgId));
    } catch (e) {
      setError((e as Error).message);
    }
  }, [getApiToken, orderId, orgId]);

  useEffect(() => {
    void load();
  }, [load]);

  async function choose(file: File | undefined) {
    if (!file || !getApiToken) return;
    setError(null);
    const preview =
      file.type.startsWith("image/") && !/heic|heif/i.test(file.type)
        ? URL.createObjectURL(file)
        : null;
    let kind = "pickup_authorization";
    let stop: "pickup" | "dropoff" = "pickup";
    try {
      const s = await attachmentsApi.suggest(await getApiToken(), file, orgId);
      kind = s.kind;
      stop = s.stop;
    } catch (e) {
      setError((e as Error).message);
      return;
    }
    setPending({ file, preview, kind, stop, required: stop === "pickup", save: false, note: "" });
  }

  async function save() {
    if (!pending || !getApiToken) return;
    setBusy(true);
    setError(null);
    try {
      await attachmentsApi.upload(
        await getApiToken(),
        orderId,
        pending.file,
        {
          kind: pending.kind,
          stop: pending.stop,
          required: pending.required,
          note: pending.note,
          saveForLocation: pending.save,
        },
        orgId
      );
      setPending(null);
      await load();
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  }

  async function remove(id: string) {
    if (!getApiToken || !window.confirm("Remove this document from the booking?")) return;
    try {
      await attachmentsApi.remove(await getApiToken(), id, orgId);
      await load();
    } catch (e) {
      setError((e as Error).message);
    }
  }

  const kinds = data?.kinds ?? {};
  const editable = data?.editable ?? { pickup: false, dropoff: false };
  const anyEditable = canWrite && (editable.pickup || editable.dropoff);

  return (
    <Card title="Pickup & delivery documents">
      <p className="mb-3 text-sm text-muted">
        Only the driver assigned to this booking can open these, and only at their stop. They are
        removed 90 days after delivery.
      </p>

      {(data?.items ?? []).length > 0 && (
        <ul className="mb-4 divide-y divide-primary/10">
          {data!.items.map((a) => (
            <li key={a.id} className="flex flex-wrap items-center gap-2 py-2 text-sm">
              <button
                type="button"
                className="font-medium text-secondary hover:underline"
                onClick={async () =>
                  getApiToken && attachmentsApi.open(await getApiToken(), a.id, orgId)
                }
                disabled={a.purged}
              >
                {a.filename}
              </button>
              <span className="text-muted">
                {a.kind_label} · {a.stop === "pickup" ? "Pickup stop" : "Drop-off stop"}
                {a.required_at_stop ? " · Must be shown" : ""}
                {a.from_location_template ? " · Saved for this address" : ""}
              </span>
              <span className={`rounded-full px-2 py-0.5 text-xs ${STATUS[a.status].cls}`}>
                {STATUS[a.status].label}
              </span>
              {canWrite && editable[a.stop] && (
                <button
                  type="button"
                  className="ml-auto text-xs text-red-600 hover:underline"
                  onClick={() => void remove(a.id)}
                >
                  Remove
                </button>
              )}
            </li>
          ))}
        </ul>
      )}

      {anyEditable && !pending && (
        <div
          onDragOver={(e) => {
            e.preventDefault();
            setDrag(true);
          }}
          onDragLeave={() => setDrag(false)}
          onDrop={(e) => {
            e.preventDefault();
            setDrag(false);
            void choose(e.dataTransfer.files?.[0]);
          }}
          className={`rounded-xl border-2 border-dashed p-5 text-center text-sm ${drag ? "border-secondary bg-secondary/5" : "border-primary/20"}`}
        >
          <p className="font-medium">Drop a pickup document here</p>
          <p className="text-muted">PDF, JPG, PNG or HEIC, up to 10 MB</p>
          <div className="mt-3 flex justify-center gap-2">
            <Button size="sm" onClick={() => pickRef.current?.click()}>
              Attach document
            </Button>
            <Button size="sm" variant="outline" onClick={() => camRef.current?.click()}>
              Take photo
            </Button>
          </div>
          <input
            ref={pickRef}
            type="file"
            accept={ACCEPT}
            hidden
            onChange={(e) => void choose(e.target.files?.[0])}
          />
          <input
            ref={camRef}
            type="file"
            accept="image/*"
            capture="environment"
            hidden
            onChange={(e) => void choose(e.target.files?.[0])}
          />
        </div>
      )}

      {pending && (
        <div className="space-y-3 rounded-xl border border-primary/15 p-4 text-sm">
          <div className="flex items-start gap-3">
            {pending.preview ? (
              // eslint-disable-next-line @next/next/no-img-element
              <img src={pending.preview} alt="" className="h-20 w-16 rounded object-cover" />
            ) : (
              <div className="flex h-20 w-16 items-center justify-center rounded bg-primary/5 text-xs">
                PDF
              </div>
            )}
            <div>
              <p className="font-medium">{pending.file.name}</p>
              <p className="text-muted">We suggested a type. Change it if it's wrong.</p>
            </div>
          </div>
          <label className="block">
            Document type
            <select
              className="mt-1 block w-full rounded border p-2"
              value={pending.kind}
              onChange={(e) => setPending({ ...pending, kind: e.target.value })}
            >
              {Object.entries(kinds).map(([k, v]) => (
                <option key={k} value={k}>
                  {v}
                </option>
              ))}
            </select>
          </label>
          <label className="block">
            Stop
            <select
              className="mt-1 block w-full rounded border p-2"
              value={pending.stop}
              onChange={(e) =>
                setPending({ ...pending, stop: e.target.value as "pickup" | "dropoff" })
              }
            >
              <option value="pickup" disabled={!editable.pickup}>
                Pickup stop
              </option>
              <option value="dropoff" disabled={!editable.dropoff}>
                Drop-off stop
              </option>
            </select>
          </label>
          <label className="flex items-center gap-2">
            <input
              type="checkbox"
              checked={pending.required}
              onChange={(e) => setPending({ ...pending, required: e.target.checked })}
            />
            Driver must show this to staff before pickup
          </label>
          <label className="flex items-center gap-2">
            <input
              type="checkbox"
              checked={pending.save}
              onChange={(e) => setPending({ ...pending, save: e.target.checked })}
            />
            Use for every booking from this address
          </label>
          <label className="block">
            Note for driver (optional)
            <input
              className="mt-1 block w-full rounded border p-2"
              maxLength={500}
              value={pending.note}
              onChange={(e) => setPending({ ...pending, note: e.target.value })}
            />
          </label>
          <div className="flex gap-2">
            <Button size="sm" onClick={() => void save()} disabled={busy}>
              {busy ? "Saving…" : "Save document"}
            </Button>
            <Button size="sm" variant="outline" onClick={() => setPending(null)} disabled={busy}>
              Cancel
            </Button>
          </div>
        </div>
      )}
      {error && <p className="mt-2 text-sm text-red-600">{error}</p>}
    </Card>
  );
}
