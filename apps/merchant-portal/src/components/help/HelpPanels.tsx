"use client";

import { useState } from "react";
import Button from "@/components/ui/Button";
import { claimStatusLabel, claimTypeLabel, ticketStatusLabel } from "@/lib/catalog";
import { settingsApi, type ClaimRow, type SupportTicket, type TimelineEntry } from "@/lib/settings";
import { formatDate } from "@/lib/utils";
import { PageSkeleton } from "@porterchain/ui/loading";

function TimelineList({ entries }: { entries: TimelineEntry[] }) {
  if (!entries.length) {
    return <p className="text-sm text-muted">No activity yet.</p>;
  }
  return (
    <ul className="mt-2 space-y-2 text-sm">
      {entries.map((entry, i) => {
        const when = entry.occurred_at || entry.at || entry.created_at || "";
        return (
          <li key={`${entry.label ?? "event"}-${i}`} className="border-b border-primary/5 py-2">
            <p className="font-medium text-primary">{entry.label || "Update"}</p>
            <p className="text-xs text-muted">
              {when ? formatDate(when) : "—"}
              {entry.actor_type ? ` · ${entry.actor_type}` : ""}
            </p>
          </li>
        );
      })}
    </ul>
  );
}

export function SupportPanel({
  tickets,
  kb,
  onRefresh,
  getToken,
  orgId,
}: {
  tickets: SupportTicket[];
  kb: {
    articles: Array<{ id: string; title: string; body: string }>;
    faq: Array<{ question: string; answer: string }>;
  } | null;
  onRefresh: () => Promise<void>;
  getToken: () => Promise<string>;
  orgId?: string;
}) {
  const [subject, setSubject] = useState("");
  const [description, setDescription] = useState("");
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [detail, setDetail] = useState<SupportTicket | null>(null);
  const [detailError, setDetailError] = useState<string | null>(null);
  const [detailBusy, setDetailBusy] = useState(false);

  const create = async () => {
    const token = await getToken();
    await settingsApi.createTicket(token, { subject, description }, orgId);
    setSubject("");
    setDescription("");
    await onRefresh();
  };

  const openTicket = async (ticketId: string) => {
    setSelectedId(ticketId);
    setDetailBusy(true);
    setDetailError(null);
    try {
      const token = await getToken();
      setDetail(await settingsApi.getTicket(token, ticketId, orgId));
    } catch (e) {
      setDetail(null);
      setDetailError(e instanceof Error ? e.message : "Could not load ticket");
    } finally {
      setDetailBusy(false);
    }
  };

  return (
    <div className="space-y-6">
      <section className="rounded-2xl border border-primary/10 bg-white p-6">
        <h2 className="font-semibold text-primary">Open a support ticket</h2>
        <div className="mt-4 space-y-2">
          <input
            className="w-full rounded-lg border px-3 py-2 text-sm"
            placeholder="Subject"
            value={subject}
            onChange={(e) => setSubject(e.target.value)}
          />
          <textarea
            className="w-full rounded-lg border px-3 py-2 text-sm"
            rows={3}
            placeholder="Description"
            value={description}
            onChange={(e) => setDescription(e.target.value)}
          />
          <Button size="sm" onClick={() => void create()}>
            Submit ticket
          </Button>
        </div>
      </section>
      <section className="rounded-2xl border border-primary/10 bg-white p-6">
        <h2 className="font-semibold text-primary">Ticket history</h2>
        <ul className="mt-4 space-y-2 text-sm">
          {tickets.length === 0 && <li className="text-muted">No tickets yet</li>}
          {tickets.map((t) => (
            <li key={t.ticket_id}>
              <button
                type="button"
                onClick={() => void openTicket(t.ticket_id)}
                className={`flex w-full justify-between gap-4 border-b border-primary/5 py-2 text-left ${
                  selectedId === t.ticket_id ? "text-secondary" : "hover:text-secondary"
                }`}
              >
                <span>{t.subject}</span>
                <span className="shrink-0 text-muted">
                  {ticketStatusLabel(t.status)} · {t.created_at ? formatDate(t.created_at) : ""}
                </span>
              </button>
            </li>
          ))}
        </ul>
        {selectedId ? (
          <div className="mt-4 rounded-xl border border-primary/10 bg-gray-bg p-4">
            {detailBusy && <PageSkeleton rows={2} />}
            {detailError && <p className="text-sm text-red-600">{detailError}</p>}
            {detail && !detailBusy ? (
              <div className="space-y-3">
                <div className="flex items-start justify-between gap-3">
                  <div>
                    <p className="font-semibold text-primary">{detail.subject}</p>
                    <p className="text-xs text-muted">
                      {detail.ticket_number || detail.ticket_id} ·{" "}
                      {ticketStatusLabel(detail.status)}
                    </p>
                  </div>
                  <button
                    type="button"
                    className="text-xs text-muted underline"
                    onClick={() => {
                      setSelectedId(null);
                      setDetail(null);
                    }}
                  >
                    Close
                  </button>
                </div>
                {detail.description ? (
                  <p className="text-sm text-primary whitespace-pre-wrap">{detail.description}</p>
                ) : null}
                <div>
                  <h3 className="text-sm font-semibold text-primary">Timeline</h3>
                  <TimelineList entries={detail.timeline || []} />
                </div>
                <p className="text-xs text-muted">
                  Replies from PorterChain appear here. Merchant reply is coming next.
                </p>
              </div>
            ) : null}
          </div>
        ) : null}
      </section>
      {kb && (
        <section className="rounded-2xl border border-primary/10 bg-white p-6">
          <h2 className="font-semibold text-primary">Knowledge base</h2>
          <ul className="mt-4 space-y-4 text-sm">
            {kb.articles.map((a) => (
              <li key={a.id}>
                <p className="font-medium">{a.title}</p>
                <p className="text-muted">{a.body}</p>
              </li>
            ))}
          </ul>
        </section>
      )}
    </div>
  );
}

export function ClaimsPanel({
  claims,
  onRefresh,
  getToken,
  orgId,
}: {
  claims: ClaimRow[];
  onRefresh: () => Promise<void>;
  getToken: () => Promise<string>;
  orgId?: string;
}) {
  const [orderRef, setOrderRef] = useState("");
  const [claimType, setClaimType] = useState("merchant_complaint");
  const [description, setDescription] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [detail, setDetail] = useState<ClaimRow | null>(null);
  const [detailError, setDetailError] = useState<string | null>(null);
  const [detailBusy, setDetailBusy] = useState(false);

  const file = async () => {
    const lookup = orderRef.trim();
    if (!lookup) {
      setError("Enter an order number or tracking number.");
      return;
    }
    setError(null);
    setBusy(true);
    try {
      const token = await getToken();
      await settingsApi.openClaim(
        token,
        { order_number: lookup, claim_type: claimType, description },
        orgId
      );
      setOrderRef("");
      setDescription("");
      await onRefresh();
    } catch (e) {
      setError(e instanceof Error ? e.message : "That order was not found.");
    } finally {
      setBusy(false);
    }
  };

  const openClaim = async (claimId: string) => {
    setSelectedId(claimId);
    setDetailBusy(true);
    setDetailError(null);
    try {
      const token = await getToken();
      setDetail(await settingsApi.getClaim(token, claimId, orgId));
    } catch (e) {
      setDetail(null);
      setDetailError(e instanceof Error ? e.message : "Could not load claim");
    } finally {
      setDetailBusy(false);
    }
  };

  return (
    <div className="space-y-6">
      <section className="rounded-2xl border border-primary/10 bg-white p-6">
        <h2 className="font-semibold text-primary">File a claim</h2>
        <div className="mt-4 space-y-2">
          <input
            className="w-full rounded-lg border px-3 py-2 text-sm"
            placeholder="Order or tracking number"
            value={orderRef}
            onChange={(e) => setOrderRef(e.target.value)}
          />
          <select
            className="w-full rounded-lg border px-3 py-2 text-sm"
            value={claimType}
            onChange={(e) => setClaimType(e.target.value)}
          >
            <option value="merchant_complaint">Merchant complaint</option>
            <option value="damaged_parcel">Damaged parcel</option>
            <option value="lost_parcel">Lost parcel</option>
            <option value="late_delivery">Late delivery</option>
          </select>
          <textarea
            className="w-full rounded-lg border px-3 py-2 text-sm"
            rows={3}
            placeholder="Description"
            value={description}
            onChange={(e) => setDescription(e.target.value)}
          />
          {error && <p className="text-sm text-red-600">{error}</p>}
          <Button size="sm" disabled={busy} onClick={() => void file()}>
            Submit claim
          </Button>
        </div>
      </section>
      <section className="rounded-2xl border border-primary/10 bg-white p-6">
        <h2 className="font-semibold text-primary">Claims history</h2>
        <ul className="mt-4 space-y-2 text-sm">
          {claims.length === 0 && <li className="text-muted">No claims</li>}
          {claims.map((c) => (
            <li key={c.claim_id}>
              <button
                type="button"
                onClick={() => void openClaim(c.claim_id)}
                className={`flex w-full justify-between gap-4 border-b border-primary/5 py-2 text-left ${
                  selectedId === c.claim_id ? "text-secondary" : "hover:text-secondary"
                }`}
              >
                <span>
                  {c.claim_number} · {claimTypeLabel(c.claim_type)}
                  {c.order_number || c.tracking_number ? (
                    <span className="block text-xs text-muted">
                      {c.order_number ?? ""}
                      {c.order_number && c.tracking_number ? " · " : ""}
                      {c.tracking_number ?? ""}
                    </span>
                  ) : null}
                </span>
                <span className="shrink-0 text-muted">{claimStatusLabel(c.status)}</span>
              </button>
            </li>
          ))}
        </ul>
        {selectedId ? (
          <div className="mt-4 rounded-xl border border-primary/10 bg-gray-bg p-4">
            {detailBusy && <PageSkeleton rows={2} />}
            {detailError && <p className="text-sm text-red-600">{detailError}</p>}
            {detail && !detailBusy ? (
              <div className="space-y-3">
                <div className="flex items-start justify-between gap-3">
                  <div>
                    <p className="font-semibold text-primary">
                      {detail.claim_number} · {claimTypeLabel(detail.claim_type)}
                    </p>
                    <p className="text-xs text-muted">{claimStatusLabel(detail.status)}</p>
                  </div>
                  <button
                    type="button"
                    className="text-xs text-muted underline"
                    onClick={() => {
                      setSelectedId(null);
                      setDetail(null);
                    }}
                  >
                    Close
                  </button>
                </div>
                {detail.description ? (
                  <p className="text-sm text-primary whitespace-pre-wrap">{detail.description}</p>
                ) : null}
                <div>
                  <h3 className="text-sm font-semibold text-primary">Timeline</h3>
                  <TimelineList entries={detail.timeline || []} />
                </div>
              </div>
            ) : null}
          </div>
        ) : null}
      </section>
    </div>
  );
}
