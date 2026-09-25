"use client";

import Link from "next/link";
import { useState } from "react";
import Button from "@/components/ui/Button";
import { ticketStatusLabel } from "@/lib/catalog";
import { ordersApi, type OrderDetail } from "@/lib/orders";
import { settingsApi } from "@/lib/settings";
import { formatDate } from "@/lib/utils";
import { Card } from "./shared";

export function SupportTab({
  tickets,
  orderId,
  getApiToken,
  orgId,
  onRefresh,
}: {
  tickets: Array<Record<string, unknown>>;
  orderId: string;
  getApiToken?: () => Promise<string>;
  orgId?: string;
  onRefresh: () => void;
}) {
  const [subject, setSubject] = useState("");
  const [description, setDescription] = useState("");
  const [submitting, setSubmitting] = useState(false);

  const submit = async () => {
    if (!getApiToken || !subject.trim()) return;
    setSubmitting(true);
    try {
      const token = await getApiToken();
      await settingsApi.createTicket(
        token,
        { subject, description, order_id: orderId, category: "merchant_support" },
        orgId
      );
      setSubject("");
      setDescription("");
      onRefresh();
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <Card title="Support tickets">
      {getApiToken && (
        <div className="mb-4 space-y-2 border-b border-primary/10 pb-4">
          <input
            className="w-full rounded-lg border px-3 py-2 text-sm"
            placeholder="Subject"
            value={subject}
            onChange={(e) => setSubject(e.target.value)}
          />
          <textarea
            className="w-full rounded-lg border px-3 py-2 text-sm"
            rows={2}
            placeholder="Description"
            value={description}
            onChange={(e) => setDescription(e.target.value)}
          />
          <Button size="sm" onClick={() => void submit()} disabled={submitting}>
            Open ticket
          </Button>
        </div>
      )}
      {tickets.length === 0 ? (
        <p className="text-muted">No support tickets for this order.</p>
      ) : (
        <ul className="space-y-2">
          {tickets.map((t) => (
            <li key={String(t.id)} className="rounded-lg border border-primary/10 p-3">
              <p className="font-medium">{String(t.subject)}</p>
              <p className="text-muted">
                {ticketStatusLabel(String(t.status))}
                {t.created_at ? ` · ${formatDate(String(t.created_at))}` : ""}
              </p>
            </li>
          ))}
        </ul>
      )}
    </Card>
  );
}
