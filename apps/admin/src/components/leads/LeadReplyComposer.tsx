"use client";

import { useEffect, useState } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { Mail, MessageCircle, Phone, Sparkles } from "lucide-react";
import { cn } from "@porterchain/ui/utils";
import { Button } from "@/components/crm/primitives";
import { useAdminAuth } from "@/hooks/useAdminAuth";
import type { Lead } from "@/lib/crm";
import {
  leadsApi,
  replyDisabledReason,
  type ReplyChannelStatus,
  type ReplyPrefill,
} from "@/lib/leads";

type Tab = "email" | "whatsapp" | "call";

const CALL_OUTCOME_LABELS: Record<string, string> = {
  connected: "Connected",
  no_answer: "No answer",
  voicemail: "Left voicemail",
  callback: "Call back later",
  interested: "Interested",
  quote_requested: "Wants a quote",
  not_interested: "Not interested",
  wrong_number: "Wrong number",
};

/**
 * One place to answer a lead: email (ZeptoMail / Zoho SMTP from sales@),
 * WhatsApp (Cloud API, 24 h window) or "Log a call" for the mobile.
 * Nothing sends until staff press Send — no automatic replies.
 */
export default function LeadReplyComposer({
  lead,
  prefill,
}: {
  lead: Lead;
  prefill?: ReplyPrefill | null;
}) {
  const { getApiToken, isLoaded, isSignedIn } = useAdminAuth();
  const qc = useQueryClient();
  const [tab, setTab] = useState<Tab>(lead.channel === "whatsapp" ? "whatsapp" : "email");
  const [subject, setSubject] = useState(`Re: your PorterChain inquiry`);
  const [body, setBody] = useState("");
  const [direction, setDirection] = useState<"outbound" | "inbound">("outbound");
  const [outcome, setOutcome] = useState("connected");
  const [minutes, setMinutes] = useState("");
  const [followUp, setFollowUp] = useState("");
  const [busy, setBusy] = useState(false);
  const [result, setResult] = useState<{ ok: boolean; text: string } | null>(null);
  const [attachQuote, setAttachQuote] = useState(false);
  const [drafting, setDrafting] = useState(false);

  // "Send quote" / AI draft fill the composer — the admin still presses Send.
  useEffect(() => {
    if (!prefill) return;
    setTab(prefill.channel);
    if (prefill.subject) setSubject(prefill.subject);
    setBody(prefill.body);
    setAttachQuote(prefill.attachQuote);
    setResult(null);
  }, [prefill]);

  // Instant draft: a new, unanswered lead opens with a ready reply (never sent).
  const [autoDrafted, setAutoDrafted] = useState(false);
  useEffect(() => {
    if (autoDrafted || prefill || !isLoaded) return;
    if (lead.first_response_at || !["new"].includes(lead.status)) return;
    setAutoDrafted(true);
    void (async () => {
      try {
        const ch = lead.channel === "whatsapp" || (!lead.email && lead.phone) ? "whatsapp" : "email";
        const d = await leadsApi.draft(await getApiToken(), lead.id, ch, false);
        setBody((cur) => (cur.trim() ? cur : d.body));
        if (d.subject) setSubject(d.subject);
        setTab(ch);
      } catch {
        /* drafts are best-effort */
      }
    })();
  }, [autoDrafted, prefill, isLoaded, lead, getApiToken]);

  const draft = async () => {
    if (tab === "call") return;
    setDrafting(true);
    setResult(null);
    try {
      const d = await leadsApi.draft(await getApiToken(), lead.id, tab, false);
      if (d.subject) setSubject(d.subject);
      setBody(d.body);
      setAttachQuote(false);
    } catch (e) {
      setResult({ ok: false, text: e instanceof Error ? e.message : "draft_failed" });
    } finally {
      setDrafting(false);
    }
  };

  const { data: channels } = useQuery({
    queryKey: ["lead-reply-channels", lead.id],
    enabled: isLoaded && (isSignedIn || process.env.NODE_ENV === "development"),
    queryFn: async () => leadsApi.replyChannels(await getApiToken(), lead.id),
  });

  const status: ReplyChannelStatus | undefined =
    tab === "email" ? channels?.email : tab === "whatsapp" ? channels?.whatsapp : undefined;
  const disabled = tab !== "call" && !status?.enabled;

  const refresh = async () => {
    await Promise.all([
      qc.invalidateQueries({ queryKey: ["lead", lead.id] }),
      qc.invalidateQueries({ queryKey: ["lead-conversations", lead.id] }),
      qc.invalidateQueries({ queryKey: ["lead-reply-channels", lead.id] }),
      qc.invalidateQueries({ queryKey: ["leads"] }),
    ]);
  };

  const submit = async () => {
    setBusy(true);
    setResult(null);
    try {
      const token = await getApiToken();
      if (tab === "call") {
        await leadsApi.logCall(token, lead.id, {
          direction,
          outcome,
          notes: body.trim() || undefined,
          duration_minutes: minutes ? Number(minutes) : undefined,
          follow_up_at: followUp ? new Date(followUp).toISOString() : undefined,
        });
        setResult({ ok: true, text: "Call logged." });
      } else {
        if (!body.trim()) return;
        const out = await leadsApi.reply(token, lead.id, {
          channel: tab,
          body: body.trim(),
          ...(tab === "email" ? { subject: subject.trim() || undefined } : {}),
          ...(attachQuote ? { attach_quote: true } : {}),
        });
        setResult({ ok: true, text: `${attachQuote ? "Quote sent" : "Sent"} to ${out.to ?? "lead"}.` });
        setAttachQuote(false);
      }
      setBody("");
      setMinutes("");
      setFollowUp("");
      await refresh();
    } catch (e) {
      const code = e instanceof Error ? e.message : "send_failed";
      setResult({ ok: false, text: replyDisabledReason(code) });
    } finally {
      setBusy(false);
    }
  };

  const tabBtn = (key: Tab, label: string, Icon: typeof Mail, s?: ReplyChannelStatus) => (
    <button
      type="button"
      role="tab"
      aria-selected={tab === key}
      onClick={() => {
        setTab(key);
        setResult(null);
      }}
      className={cn(
        "inline-flex items-center gap-1.5 rounded-full px-3.5 py-1.5 text-sm font-semibold",
        tab === key ? "bg-primary text-white" : "text-slate-700 hover:bg-slate-100"
      )}
    >
      <Icon className="h-4 w-4" aria-hidden />
      {label}
      {s && !s.enabled ? (
        <span className="rounded bg-slate-200 px-1 text-[10px] uppercase text-slate-600">off</span>
      ) : null}
    </button>
  );

  const input =
    "w-full rounded-2xl border border-primary/15 px-3.5 py-2.5 text-sm text-primary focus:border-secondary focus:outline-none";

  return (
    <section
      id="lead-reply"
      className="scroll-mt-24 rounded-3xl border border-primary/10 bg-white p-4 sm:p-6"
      aria-label="Reply to lead"
    >
      <div className="mb-3 flex flex-wrap items-center justify-between gap-2">
        <div className="flex flex-wrap gap-1" role="tablist" aria-label="Reply channel">
          {tabBtn("email", "Email", Mail, channels?.email)}
          {tabBtn("whatsapp", "WhatsApp", MessageCircle, channels?.whatsapp)}
          {tabBtn("call", "Log a call", Phone)}
        </div>
        {lead.first_response_at ? (
          <p className="text-xs text-slate-600">
            First reply {new Date(lead.first_response_at).toLocaleString()}
          </p>
        ) : lead.awaiting_reply ? (
          <p className="text-xs font-semibold text-red-700">Awaiting your reply</p>
        ) : null}
      </div>


      {tab === "email" ? (
        <div className="space-y-2">
          <p className="text-xs text-muted">
            To <span className="font-medium text-primary">{lead.email ?? "—"}</span> · from{" "}
            {channels?.email.from ?? "sales@"}
            {channels?.email.transport ? ` via ${channels.email.transport}` : ""}
          </p>
          <input
            className={input}
            value={subject}
            onChange={(e) => setSubject(e.target.value)}
            aria-label="Subject"
            disabled={disabled}
          />
        </div>
      ) : null}
      {tab === "whatsapp" && channels?.whatsapp.window_closes_at && channels.whatsapp.enabled ? (
        <p className="mb-2 text-xs text-muted">
          24 h window closes {new Date(channels.whatsapp.window_closes_at).toLocaleString()}
        </p>
      ) : null}

      {tab === "call" ? (
        <div className="grid gap-2 sm:grid-cols-4">
          <select
            className={input}
            value={direction}
            onChange={(e) => setDirection(e.target.value as "outbound" | "inbound")}
            aria-label="Call direction"
          >
            <option value="outbound">I called them</option>
            <option value="inbound">They called me</option>
          </select>
          <select
            className={input}
            value={outcome}
            onChange={(e) => setOutcome(e.target.value)}
            aria-label="Call outcome"
          >
            {(channels?.call_outcomes ?? Object.keys(CALL_OUTCOME_LABELS)).map((o) => (
              <option key={o} value={o}>
                {CALL_OUTCOME_LABELS[o] ?? o}
              </option>
            ))}
          </select>
          <input
            className={input}
            type="number"
            min={0}
            max={600}
            placeholder="Minutes"
            value={minutes}
            onChange={(e) => setMinutes(e.target.value)}
            aria-label="Call length in minutes"
          />
          <input
            className={input}
            type="datetime-local"
            value={followUp}
            onChange={(e) => setFollowUp(e.target.value)}
            aria-label="Follow-up reminder"
            title="Optional follow-up reminder (creates a task)"
          />
        </div>
      ) : null}

      {tab !== "call" ? (
        <div className="mt-3 flex flex-wrap items-center gap-2">
          <button
            type="button"
            onClick={() => void draft()}
            disabled={drafting}
            className="inline-flex items-center gap-1.5 rounded-full border border-primary/15 px-3 py-1.5 text-xs font-semibold text-primary hover:bg-slate-50 disabled:opacity-50"
          >
            <Sparkles className="h-3.5 w-3.5 text-secondary" aria-hidden />
            {drafting ? "Drafting…" : "Draft reply"}
          </button>
          {attachQuote ? (
            <span className="rounded-full bg-secondary/10 px-3 py-1 text-xs font-semibold text-secondary">
              Quote attached · lead moves to Quoted on send
            </span>
          ) : null}
        </div>
      ) : null}
      <textarea
        id="lead-reply-body"
        className={cn(input, "mt-2 min-h-[140px]")}
        placeholder={tab === "call" ? "What was said? (optional)" : `Write your ${tab} reply…`}
        value={body}
        onChange={(e) => setBody(e.target.value)}
        aria-label={tab === "call" ? "Call notes" : "Reply message"}
        disabled={disabled}
      />
      <div className="mt-2 flex flex-wrap items-center justify-between gap-2">
        <p className="flex items-center gap-1.5 text-xs text-slate-600" role="note">
          {tab !== "call" && status && !status.enabled ? (
            <>
              <span className="h-1.5 w-1.5 rounded-full bg-amber-500" aria-hidden />
              {tab === "email" ? "Email" : "WhatsApp"} sending is off · {replyDisabledReason(status.reason)}
            </>
          ) : tab === "call" ? (
            "Logged to the timeline; a live conversation counts as the first reply."
          ) : (
            "Nothing sends until you press Send."
          )}
        </p>
        <Button
          onClick={() => void submit()}
          disabled={busy || disabled || (tab !== "call" && !body.trim())}
          className="rounded-full px-6"
        >
          {busy ? "Working…" : tab === "call" ? "Log call" : attachQuote ? "Send quote" : "Send"}
        </Button>
      </div>
      {result ? (
        <p
          className={cn("mt-2 text-sm", result.ok ? "text-green-700" : "text-red-700")}
          role={result.ok ? "status" : "alert"}
        >
          {result.text}
        </p>
      ) : null}
    </section>
  );
}
