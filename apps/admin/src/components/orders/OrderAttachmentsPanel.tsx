"use client";

import { useQuery } from "@tanstack/react-query";
import { useState } from "react";
import { adminFetch } from "@/lib/api";
import { downloadOrderFile } from "@/lib/orders";

type Item = {
  id: string;
  stop: string;
  kind_label: string;
  filename: string;
  required_at_stop: boolean;
  status: string;
  shown_at: string | null;
  has_proof_photo: boolean;
  purged: boolean;
  deleted: boolean;
  uploaded_by: string | null;
  from_location_template: boolean;
};
type Ev = { attachment_id: string; actor_type: string; actor_id: string | null; action: string; at: string | null };

const STATUS: Record<string, string> = {
  waiting: "Not opened",
  viewed_by_driver: "Viewed by driver",
  shown_at_pickup: "Shown at pickup",
};
const fmt = (s: string | null) =>
  s ? new Date(s).toLocaleString("en-CA", { timeZone: "America/Toronto", dateStyle: "medium", timeStyle: "short" }) + " ET" : "—";

export function OrderAttachmentsPanel({ orderId, getApiToken }: { orderId: string; getApiToken: () => Promise<string> }) {
  const [err, setErr] = useState<string | null>(null);
  const { data } = useQuery({
    queryKey: ["order-attachments", orderId],
    queryFn: async () => adminFetch<{ items: Item[]; events: Ev[] }>(`/v1/admin/orders/${orderId}/attachments`, await getApiToken()),
  });
  if (!data || (data.items.length === 0 && data.events.length === 0)) {
    return (
      <section className="rounded-xl border bg-white p-4 text-sm" data-testid="order-attachments">
        <h3 className="font-semibold">Booking documents</h3>
        <p className="text-gray-500">No documents attached.</p>
      </section>
    );
  }
  const names = Object.fromEntries(data.items.map((i) => [i.id, i.filename]));
  async function dl(id: string, name: string, proof = false) {
    try {
      await downloadOrderFile(await getApiToken(), `/v1/admin/attachments/${id}/file${proof ? "?proof=true" : ""}`, name);
    } catch (e) {
      setErr((e as Error).message);
    }
  }
  return (
    <section className="rounded-xl border bg-white p-4 text-sm" data-testid="order-attachments">
      <h3 className="font-semibold">Booking documents</h3>
      <table className="mt-2 w-full text-left">
        <thead className="text-xs uppercase text-gray-500">
          <tr>
            <th>File</th>
            <th>Type</th>
            <th>Stop</th>
            <th>Status</th>
            <th>Uploaded by</th>
            <th />
          </tr>
        </thead>
        <tbody>
          {data.items.map((i) => (
            <tr key={i.id} className={`border-t ${i.deleted ? "text-gray-400 line-through" : ""}`}>
              <td className="py-1">{i.filename}{i.from_location_template ? " (saved for address)" : ""}</td>
              <td>{i.kind_label}{i.required_at_stop ? " · required" : ""}</td>
              <td>{i.stop}</td>
              <td>{i.purged ? "Purged (retention)" : STATUS[i.status] ?? i.status}</td>
              <td>{i.uploaded_by ?? "—"}</td>
              <td className="space-x-2 text-right">
                {!i.purged && !i.deleted && (
                  <button type="button" className="text-blue-700 hover:underline" onClick={() => void dl(i.id, i.filename)}>
                    Open
                  </button>
                )}
                {i.has_proof_photo && (
                  <button type="button" className="text-blue-700 hover:underline" onClick={() => void dl(i.id, `proof-${i.filename}.jpg`, true)}>
                    Proof photo
                  </button>
                )}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
      <h4 className="mt-4 font-semibold">History</h4>
      <ul className="mt-1 space-y-0.5 text-xs text-gray-600">
        {data.events.map((e, n) => (
          <li key={n}>
            {fmt(e.at)} · {e.actor_type}
            {e.actor_id ? ` ${e.actor_id}` : ""} · {e.action.replace(/_/g, " ")} · {names[e.attachment_id] ?? e.attachment_id}
          </li>
        ))}
      </ul>
      {err && <p className="mt-2 text-red-600">{err}</p>}
    </section>
  );
}
