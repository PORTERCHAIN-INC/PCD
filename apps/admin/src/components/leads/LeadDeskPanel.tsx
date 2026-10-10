"use client";

import { useState } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { MessageCircle, Phone, Send } from "lucide-react";
import { cn } from "@porterchain/ui/utils";
import { useAdminAuth } from "@/hooks/useAdminAuth";
import type { Lead } from "@/lib/crm";
import { LOST_REASONS, dialDigits, leadsApi, type ReplyPrefill } from "@/lib/leads";
import { scoreTone } from "@/components/leads/LeadRow";

const QUOTE_REASON: Record<string, string> = {
  no_postal_code: "Add a postal code to price this lead.",
  outside_service_area: "Postal code is outside the GTA service area.",
};

/**
 * Lead desk: fit score (with reasons), instant quote → 1-click "Send quote",
 * one-tap lost reason, and a thumb-reach action bar on phones.
 * Nothing here sends: "Send quote" only fills the composer.
 */
export default function LeadDeskPanel({
  lead,
  onPrefill,
}: {
  lead: Lead;
  onPrefill: (p: ReplyPrefill) => void;
}) {
  const { getApiToken, isLoaded, isSignedIn } = useAdminAuth();
  const enabled = isLoaded && (isSignedIn || process.env.NODE_ENV === "development");
  const [busy, setBusy] = useState<string | null>(null);
  const [error, setError] = useState("");

  const { data: quote, isLoading: quoteLoading } = useQuery({
    queryKey: ["lead-quote", lead.id],
    enabled,
    queryFn: async () => leadsApi.quote(await getApiToken(), lead.id),
  });
  const { data: score } = useQuery({
    queryKey: ["lead-fit", lead.id, lead.lead_score],
    enabled,
    queryFn: async () => leadsApi.fitScore(await getApiToken(), lead.id),
  });

  const preferred: "email" | "whatsapp" =
    lead.channel === "whatsapp" || (!lead.email && lead.phone) ? "whatsapp" : "email";

  const sendQuote = async () => {
    setBusy("quote");
    setError("");
    try {
      const d = await leadsApi.draft(await getApiToken(), lead.id, preferred, true);
      onPrefill({ channel: d.channel, subject: d.subject, body: d.body, attachQuote: d.with_quote, nonce: Date.now() });
      document.getElementById("lead-reply")?.scrollIntoView({ behavior: "smooth", block: "start" });
    } catch (e) {
      setError(e instanceof Error ? e.message : "draft_failed");
    } finally {
      setBusy(null);
    }
  };

  const digits = dialDigits(lead.phone);
  const s = score?.score ?? lead.lead_score;
  const tone = scoreTone(s);

  return (
    <>
      <div className="grid gap-4 lg:grid-cols-5">
        {/* Instant quote — the one primary action */}
        <section
          aria-label="Instant quote"
          className="rounded-3xl bg-primary p-6 text-white lg:col-span-3"
        >
          <p className="text-[11px] font-semibold uppercase tracking-[0.14em] text-slate-300">
            Instant quote
          </p>
          {quoteLoading ? (
            <div className="mt-3 h-12 w-40 animate-pulse rounded-xl bg-white/10" aria-busy="true" />
          ) : quote?.available ? (
            <>
              <p className="mt-2 text-4xl font-extrabold tracking-tight tabular-nums sm:text-5xl">
                {quote.amount_display}
                <span className="ml-2 text-base font-semibold text-slate-300">CAD incl. HST</span>
              </p>
              <p className="mt-2 text-sm text-slate-200">
                {quote.vehicle_label} · {quote.pickup_fsa} → {quote.dropoff_fsa}
                {quote.distance_km ? ` · ${quote.distance_km} km` : ""}
                {quote.parcel_count > 1 ? ` · ${quote.parcel_count} parcels` : ""} ·{" "}
                {quote.pricing === "merchant" ? "merchant rates" : "retail rates"}
              </p>
              <div className="mt-5 flex flex-wrap items-center gap-3">
                <button
                  type="button"
                  data-send-quote
                  onClick={() => void sendQuote()}
                  disabled={busy !== null}
                  className="inline-flex items-center gap-2 rounded-full bg-sky-400 px-6 py-3 text-sm font-extrabold text-primary hover:bg-sky-300 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-white disabled:opacity-60"
                >
                  <Send className="h-4 w-4" aria-hidden />
                  {busy === "quote" ? "Preparing…" : "Send quote"}
                </button>
                <span className="text-xs text-slate-300">Fills the reply with price + booking link. You press Send.</span>
              </div>
            </>
          ) : (
            <p className="mt-2 text-sm text-slate-200">
              {QUOTE_REASON[quote?.reason ?? ""] ?? "No quote available for this lead yet."}
            </p>
          )}
        </section>

        {/* Fit score */}
        <section aria-label="Lead score" className="rounded-3xl border border-primary/10 bg-white p-6 lg:col-span-2">
          <div className="flex items-baseline justify-between">
            <p className="text-[11px] font-semibold uppercase tracking-[0.14em] text-slate-500">Fit score</p>
            <p className={cn("text-4xl font-extrabold tabular-nums", tone)}>
              {s}
              <span className="text-base font-semibold text-slate-500">/100</span>
            </p>
          </div>
          <ul className="mt-3 space-y-1.5 text-sm">
            {(score?.reasons ?? []).map((r) => (
              <li key={r.label} className="flex justify-between gap-3">
                <span className="text-slate-700">{r.label}</span>
                <span className="font-mono font-semibold text-primary">+{r.points}</span>
              </li>
            ))}
          </ul>
        </section>
      </div>

      {error ? (
        <p role="alert" className="text-sm text-red-700">
          {error}
        </p>
      ) : null}

      {/* Phone: thumb-reach actions */}
      <nav
        aria-label="Quick actions"
        className="fixed inset-x-0 bottom-0 z-40 grid grid-cols-3 gap-2 border-t border-primary/10 bg-white/95 px-3 pb-[max(0.75rem,env(safe-area-inset-bottom))] pt-3 backdrop-blur md:hidden"
      >
        <a
          href={digits ? `tel:+${digits}` : undefined}
          aria-disabled={!digits}
          className={cn(
            "flex flex-col items-center gap-1 rounded-2xl border border-primary/15 py-2 text-xs font-bold text-primary",
            !digits && "pointer-events-none opacity-40"
          )}
        >
          <Phone className="h-5 w-5" aria-hidden /> Call
        </a>
        <a
          href={digits ? `https://wa.me/${digits}` : undefined}
          target="_blank"
          rel="noreferrer"
          aria-disabled={!digits}
          className={cn(
            "flex flex-col items-center gap-1 rounded-2xl border border-primary/15 py-2 text-xs font-bold text-primary",
            !digits && "pointer-events-none opacity-40"
          )}
        >
          <MessageCircle className="h-5 w-5" aria-hidden /> WhatsApp
        </a>
        <button
          type="button"
          onClick={() => void sendQuote()}
          disabled={!quote?.available || busy !== null}
          className="flex flex-col items-center gap-1 rounded-2xl bg-secondary py-2 text-xs font-bold text-white disabled:opacity-50"
        >
          <Send className="h-5 w-5" aria-hidden /> Send quote
        </button>
      </nav>
    </>
  );
}

/** One-tap lost reason, tucked next to the status pill. */
export function LostReasonMenu({ lead }: { lead: Lead }) {
  const { getApiToken } = useAdminAuth();
  const qc = useQueryClient();
  const [busy, setBusy] = useState<string | null>(null);
  const [error, setError] = useState("");
  if (lead.status === "lost") {
    return (
      <span className="text-xs font-semibold text-slate-600">
        Lost · {LOST_REASONS.find((r) => r.key === lead.lost_reason)?.label ?? lead.lost_reason ?? "—"}
      </span>
    );
  }
  if (lead.status === "won") return null;
  const markLost = async (reason: string) => {
    setBusy(reason);
    setError("");
    try {
      await leadsApi.markLost(await getApiToken(), lead.id, reason);
      await Promise.all([
        qc.invalidateQueries({ queryKey: ["lead", lead.id] }),
        qc.invalidateQueries({ queryKey: ["leads"] }),
        qc.invalidateQueries({ queryKey: ["lead-speed"] }),
      ]);
    } catch (e) {
      setError(e instanceof Error ? e.message : "update_failed");
    } finally {
      setBusy(null);
    }
  };
  return (
    <details className="group relative">
      <summary className="cursor-pointer list-none rounded-full px-2.5 py-0.5 text-xs font-semibold text-slate-600 ring-1 ring-inset ring-primary/15 hover:bg-slate-50 [&::-webkit-details-marker]:hidden">
        Mark lost
      </summary>
      <div className="fixed inset-x-4 z-30 mt-2 flex flex-wrap gap-1.5 rounded-2xl border border-primary/10 bg-white p-3 shadow-xl sm:absolute sm:inset-x-auto sm:left-0 sm:w-[22rem]">
        {LOST_REASONS.map((r) => (
          <button
            key={r.key}
            type="button"
            disabled={busy !== null}
            onClick={() => void markLost(r.key)}
            className="rounded-full border border-primary/15 px-3 py-1.5 text-xs font-semibold text-slate-700 hover:border-red-300 hover:bg-red-50 hover:text-red-800 disabled:opacity-50"
          >
            {busy === r.key ? "…" : r.label}
          </button>
        ))}
        {error ? (
          <p role="alert" className="w-full text-xs text-red-700">
            {error}
          </p>
        ) : null}
      </div>
    </details>
  );
}
