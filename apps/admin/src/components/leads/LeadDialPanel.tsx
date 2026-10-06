"use client";

import { useRouter } from "next/navigation";
import { useCallback, useEffect, useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { useAdminAuth } from "@/hooks/useAdminAuth";
import { Button } from "@/components/crm/primitives";
import { PageSkeleton } from "@porterchain/ui/loading";

import { leadsApi } from "@/lib/leads";
import type { Lead } from "@/lib/crm";

const OUTCOMES: Array<{ key: string; label: string; hotkey: string }> = [
  { key: "no_answer", label: "No answer", hotkey: "1" },
  { key: "voicemail", label: "Voicemail", hotkey: "2" },
  { key: "busy", label: "Busy", hotkey: "3" },
  { key: "gatekeeper", label: "Gatekeeper", hotkey: "4" },
  { key: "callback", label: "Callback", hotkey: "5" },
  { key: "send_info", label: "Send info", hotkey: "6" },
  { key: "interested", label: "Interested", hotkey: "7" },
  { key: "quote_requested", label: "Quote", hotkey: "8" },
  { key: "connected_qualified", label: "Qualified", hotkey: "9" },
  { key: "not_interested", label: "Not interested", hotkey: "0" },
  { key: "wrong_number", label: "Wrong #", hotkey: "" },
  { key: "dnc", label: "DNC", hotkey: "" },
];

const LOSS = new Set(["not_interested", "wrong_number", "dnc"]);
const HOTKEY_MAP = Object.fromEntries(
  OUTCOMES.filter((o) => o.hotkey).map((o) => [o.hotkey, o.key])
);

export function LeadDialPanel({ lead }: { lead: Lead }) {
  const router = useRouter();
  const { getApiToken } = useAdminAuth();
  const [outcome, setOutcome] = useState("no_answer");
  const [notes, setNotes] = useState("");
  const [lossReason, setLossReason] = useState("");
  const [contactName, setContactName] = useState(lead.primary_contact_name ?? "");
  const [email, setEmail] = useState(lead.email ?? "");
  const [phone, setPhone] = useState(lead.phone ?? "");
  const [consent, setConsent] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [msg, setMsg] = useState("");

  useEffect(() => {
    setContactName(lead.primary_contact_name ?? "");
    setEmail(lead.email ?? "");
    setPhone(lead.phone ?? "");
    setNotes("");
    setLossReason("");
    setOutcome("no_answer");
    setMsg("");
    setError("");
  }, [lead.id, lead.primary_contact_name, lead.email, lead.phone]);

  const { data: scripts, isLoading: scriptsLoading } = useQuery({
    queryKey: ["dial-scripts", lead.id],
    queryFn: async () => leadsApi.dialScripts(await getApiToken(), lead.id),
  });

  const city = typeof lead.address?.city === "string" ? lead.address.city : lead.service_area;
  const tel = (phone || lead.phone || "").replace(/\D/g, "");
  const mapsQ = useMemo(() => {
    const parts = [
      typeof lead.address?.street === "string" ? lead.address.street : "",
      city,
      typeof lead.address?.postal_code === "string" ? lead.address.postal_code : "",
    ].filter(Boolean);
    return parts.length ? encodeURIComponent(parts.join(", ")) : "";
  }, [lead.address, city]);

  const commit = useCallback(async () => {
    setBusy(true);
    setError("");
    setMsg("");
    try {
      if (LOSS.has(outcome) && !lossReason.trim()) {
        setError("Loss reason required");
        setBusy(false);
        return;
      }
      const token = await getApiToken();
      const result = await leadsApi.callDisposition(token, lead.id, {
        outcome,
        notes: notes || undefined,
        loss_reason: lossReason || undefined,
        contact_name: contactName || undefined,
        email: email || undefined,
        phone: phone || undefined,
        consent_marketing: consent || undefined,
        queue: "ready",
      });
      setMsg(`Logged ${result.outcome}`);
      if (result.next_lead_id) {
        router.push(`/leads/${result.next_lead_id}`);
      } else {
        router.refresh();
      }
    } catch (e) {
      setError(e instanceof Error ? e.message : "disposition_failed");
    } finally {
      setBusy(false);
    }
  }, [
    outcome,
    lossReason,
    notes,
    contactName,
    email,
    phone,
    consent,
    getApiToken,
    lead.id,
    router,
  ]);

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      const t = e.target as HTMLElement | null;
      if (t && (t.tagName === "INPUT" || t.tagName === "TEXTAREA" || t.isContentEditable)) {
        if (e.key === "Enter" && e.metaKey) {
          e.preventDefault();
          void commit();
        }
        return;
      }
      if (busy) return;
      const mapped = HOTKEY_MAP[e.key];
      if (mapped) {
        e.preventDefault();
        setOutcome(mapped);
        return;
      }
      if (e.key === "Enter" && !e.shiftKey) {
        e.preventDefault();
        void commit();
      }
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [busy, commit]);

  const saveFacts = async () => {
    setBusy(true);
    setError("");
    try {
      const token = await getApiToken();
      await leadsApi.update(token, lead.id, {
        primary_contact_name: contactName || null,
        email: email || null,
        phone: phone || null,
        consent: consent ? { ...(lead.consent || {}), marketing: true } : lead.consent || undefined,
      });
      setMsg("Facts saved");
    } catch (e) {
      setError(e instanceof Error ? e.message : "save_failed");
    } finally {
      setBusy(false);
    }
  };

  const sendFollowup = async () => {
    setBusy(true);
    setError("");
    try {
      const token = await getApiToken();
      await leadsApi.sendEmail(token, lead.id, "lead_outbound_followup");
      setMsg("Follow-up email queued");
    } catch (e) {
      setError(e instanceof Error ? e.message : "email_failed");
    } finally {
      setBusy(false);
    }
  };

  const runWelcome = async () => {
    setBusy(true);
    setError("");
    try {
      const token = await getApiToken();
      const result = await leadsApi.welcome(token, lead.id, { force: false });
      const channels = (result.channels || {}) as Record<
        string,
        { status?: string; reason?: string }
      >;
      const email = channels.email;
      const agent = channels.agent;
      const enrich = channels.enrich;
      if (email?.status === "sent") {
        setMsg("Agent welcomed via email");
      } else {
        setMsg(
          `Agent: ${email?.status || agent?.status || enrich?.status || "skipped"} (${email?.reason || agent?.reason || enrich?.reason || "see NBA"})`
        );
      }
      router.refresh();
    } catch (e) {
      setError(e instanceof Error ? e.message : "welcome_failed");
    } finally {
      setBusy(false);
    }
  };

  const opener = typeof scripts?.opener === "string" ? scripts.opener : "";
  const discovery = Array.isArray(scripts?.discovery) ? (scripts.discovery as string[]) : [];

  return (
    <div className="rounded-xl border border-secondary/30 bg-secondary/5 p-4">
      <div className="mb-3 flex flex-wrap items-center justify-between gap-2">
        <h2 className="text-sm font-semibold text-primary">Dial floor</h2>
        <div className="flex flex-wrap gap-2 text-sm">
          {tel ? (
            <a href={`tel:${tel}`} className="font-medium text-secondary hover:underline">
              Call {phone || lead.phone}
            </a>
          ) : (
            <span className="text-muted">No phone</span>
          )}
          {mapsQ ? (
            <a
              href={`https://www.google.com/maps/search/?api=1&query=${mapsQ}`}
              target="_blank"
              rel="noreferrer"
              className="text-muted hover:underline"
            >
              Maps
            </a>
          ) : null}
        </div>
      </div>

      <div className="grid gap-4 lg:grid-cols-2">
        <div className="space-y-3">
          <div>
            <p className="mb-1 text-xs font-medium uppercase tracking-wide text-muted">Opener</p>
            {scriptsLoading ? (
              <PageSkeleton rows={1} />
            ) : (
              <p className="text-sm text-primary">{opener || "—"}</p>
            )}
          </div>
          {discovery.length ? (
            <div>
              <p className="mb-1 text-xs font-medium uppercase tracking-wide text-muted">
                Discovery
              </p>
              <ul className="list-disc space-y-1 pl-4 text-sm text-primary">
                {discovery.map((q) => (
                  <li key={q}>{q}</li>
                ))}
              </ul>
            </div>
          ) : null}
        </div>

        <div className="space-y-2">
          <div className="grid grid-cols-2 gap-2">
            <label className="text-xs">
              Contact
              <input
                className="mt-1 w-full rounded border border-primary/15 px-2 py-1.5 text-sm"
                value={contactName}
                onChange={(e) => setContactName(e.target.value)}
              />
            </label>
            <label className="text-xs">
              Phone
              <input
                className="mt-1 w-full rounded border border-primary/15 px-2 py-1.5 text-sm"
                value={phone}
                onChange={(e) => setPhone(e.target.value)}
              />
            </label>
            <label className="col-span-2 text-xs">
              Email
              <input
                className="mt-1 w-full rounded border border-primary/15 px-2 py-1.5 text-sm"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
              />
            </label>
          </div>
          <label className="flex items-center gap-2 text-xs text-primary">
            <input
              type="checkbox"
              checked={consent}
              onChange={(e) => setConsent(e.target.checked)}
            />
            Marketing consent (required to email)
          </label>
          <div className="flex flex-wrap gap-2">
            <Button type="button" variant="outline" disabled={busy} onClick={saveFacts}>
              Save facts
            </Button>
            <Button type="button" variant="outline" disabled={busy} onClick={runWelcome}>
              Agent welcome
            </Button>
            <Button type="button" variant="outline" disabled={busy} onClick={sendFollowup}>
              Send follow-up email
            </Button>
          </div>
        </div>
      </div>

      <div className="mt-4">
        <p className="mb-2 text-xs font-medium uppercase tracking-wide text-muted">
          Outcome (hotkeys 1–9)
        </p>
        <div className="flex flex-wrap gap-1.5">
          {OUTCOMES.map((o) => (
            <button
              key={o.key}
              type="button"
              onClick={() => setOutcome(o.key)}
              className={`rounded-full border px-2.5 py-1 text-xs ${
                outcome === o.key
                  ? "border-secondary bg-secondary/15 text-secondary"
                  : "border-primary/10 text-muted hover:bg-white"
              }`}
            >
              {o.hotkey ? `${o.hotkey}. ` : ""}
              {o.label}
            </button>
          ))}
        </div>
        {LOSS.has(outcome) ? (
          <input
            className="mt-2 w-full rounded border border-primary/15 px-2 py-1.5 text-sm"
            placeholder="Loss reason (required)"
            value={lossReason}
            onChange={(e) => setLossReason(e.target.value)}
          />
        ) : null}
        <textarea
          className="mt-2 w-full rounded border border-primary/15 px-2 py-1.5 text-sm"
          rows={2}
          placeholder="Call notes"
          value={notes}
          onChange={(e) => setNotes(e.target.value)}
        />
        <div className="mt-2 flex flex-wrap items-center gap-2">
          <Button type="button" disabled={busy} onClick={commit}>
            {busy ? "Saving…" : "Log call → next"}
          </Button>
          {msg ? <span className="text-xs text-secondary">{msg}</span> : null}
          {error ? <span className="text-xs text-red-700">{error}</span> : null}
        </div>
      </div>
    </div>
  );
}
