"use client";

import Link from "next/link";
import { use, useState } from "react";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import { ArrowLeft } from "lucide-react";
import { useAdminAuth } from "@/hooks/useAdminAuth";
import { Badge, Button, Spinner } from "@/components/crm/primitives";
import {
  LEAD_PRIORITIES,
  LEAD_STATUSES,
  leadsApi,
  leadForm,
  leadIntent,
  leadMessage,
  PRIORITY_TONES,
  STATUS_TONES,
} from "@/lib/leads";

function formatWhen(iso: string): string {
  try {
    return new Intl.DateTimeFormat(undefined, {
      dateStyle: "full",
      timeStyle: "short",
    }).format(new Date(iso));
  } catch {
    return iso;
  }
}

export default function LeadDetailPage({ params }: { params: Promise<{ id: string }> }) {
  const { id } = use(params);
  const { getApiToken, isLoaded, isSignedIn } = useAdminAuth();
  const qc = useQueryClient();
  const [notes, setNotes] = useState("");
  const [saving, setSaving] = useState(false);

  const {
    data: lead,
    isLoading,
    refetch,
  } = useQuery({
    queryKey: ["lead", id],
    enabled: isLoaded && (isSignedIn || process.env.NODE_ENV === "development"),
    queryFn: async () => {
      const row = await leadsApi.detail(await getApiToken(), id);
      setNotes(row.internal_notes ?? "");
      return row;
    },
  });

  async function save(patch: { status?: string; priority?: string; internal_notes?: string }) {
    setSaving(true);
    try {
      const token = await getApiToken();
      await leadsApi.update(token, id, patch);
      await qc.invalidateQueries({ queryKey: ["lead", id] });
      await qc.invalidateQueries({ queryKey: ["leads"] });
      void refetch();
    } finally {
      setSaving(false);
    }
  }

  if (isLoading) {
    return (
      <div className="flex justify-center py-16">
        <Spinner />
      </div>
    );
  }

  if (!lead) {
    return (
      <div className="space-y-4">
        <Link href="/leads" className="inline-flex items-center gap-2 text-sm text-secondary">
          <ArrowLeft className="h-4 w-4" /> Back to leads
        </Link>
        <p className="text-muted">Lead not found.</p>
      </div>
    );
  }

  const message = leadMessage(lead);
  const intent = leadIntent(lead);
  const form = leadForm(lead);
  const custom = lead.custom_fields ?? {};
  const phoneFull = typeof custom.phone_full === "string" ? custom.phone_full : lead.phone;

  return (
    <div className="space-y-6">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <Link
            href="/leads"
            className="mb-2 inline-flex items-center gap-2 text-sm text-secondary"
          >
            <ArrowLeft className="h-4 w-4" /> Back to leads
          </Link>
          <h1 className="text-2xl font-bold text-primary">{lead.company_name}</h1>
          <p className="text-sm text-muted">{formatWhen(lead.created_at)}</p>
        </div>
        <div className="flex flex-wrap gap-2">
          <Badge tone={STATUS_TONES[lead.status] ?? "slate"}>{lead.status}</Badge>
          <Badge tone={PRIORITY_TONES[lead.priority] ?? "slate"}>{lead.priority}</Badge>
          <Badge tone="slate">Score {lead.lead_score}</Badge>
        </div>
      </div>

      <div className="grid gap-4 lg:grid-cols-2">
        <Panel title="Contact">
          <dl className="space-y-2 text-sm">
            <Row label="Name" value={lead.primary_contact_name} />
            <Row label="Email" value={lead.email} />
            <Row label="Phone" value={phoneFull} />
            <Row label="Source" value={lead.source.replace(/_/g, " ")} />
            {form && <Row label="Form" value={form} />}
            {intent && <Row label="Intent" value={intent} />}
            {typeof custom.inquiry_type === "string" && (
              <Row label="Inquiry type" value={custom.inquiry_type} />
            )}
            {typeof custom.source_page === "string" && (
              <Row label="Source page" value={custom.source_page} />
            )}
          </dl>
        </Panel>

        <Panel title="Update">
          <div className="space-y-3">
            <label className="block text-sm">
              <span className="mb-1 block font-medium text-primary">Status</span>
              <select
                value={lead.status}
                onChange={(e) => void save({ status: e.target.value })}
                disabled={saving}
                className="w-full rounded-xl border border-primary/10 px-3 py-2 text-sm"
              >
                {LEAD_STATUSES.map((s) => (
                  <option key={s} value={s}>
                    {s}
                  </option>
                ))}
              </select>
            </label>
            <label className="block text-sm">
              <span className="mb-1 block font-medium text-primary">Priority</span>
              <select
                value={lead.priority}
                onChange={(e) => void save({ priority: e.target.value })}
                disabled={saving}
                className="w-full rounded-xl border border-primary/10 px-3 py-2 text-sm"
              >
                {LEAD_PRIORITIES.map((p) => (
                  <option key={p} value={p}>
                    {p}
                  </option>
                ))}
              </select>
            </label>
            <label className="block text-sm">
              <span className="mb-1 block font-medium text-primary">Internal notes</span>
              <textarea
                value={notes}
                onChange={(e) => setNotes(e.target.value)}
                rows={4}
                className="w-full rounded-xl border border-primary/10 px-3 py-2 text-sm"
              />
            </label>
            <Button
              variant="primary"
              disabled={saving}
              onClick={() => void save({ internal_notes: notes })}
            >
              Save notes
            </Button>
          </div>
        </Panel>
      </div>

      {message && (
        <Panel title="Message">
          <p className="whitespace-pre-wrap text-sm text-primary">{message}</p>
        </Panel>
      )}

      {(typeof custom.utm_source === "string" ||
        typeof custom.utm_campaign === "string" ||
        typeof custom.utm_medium === "string") && (
        <Panel title="Attribution">
          <dl className="space-y-2 text-sm">
            {typeof custom.utm_source === "string" && (
              <Row label="UTM source" value={custom.utm_source} />
            )}
            {typeof custom.utm_campaign === "string" && (
              <Row label="UTM campaign" value={custom.utm_campaign} />
            )}
            {typeof custom.utm_medium === "string" && (
              <Row label="UTM medium" value={custom.utm_medium} />
            )}
          </dl>
        </Panel>
      )}
    </div>
  );
}

function Panel({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div className="rounded-2xl border border-primary/10 bg-white p-5">
      <h2 className="mb-4 font-semibold text-primary">{title}</h2>
      {children}
    </div>
  );
}

function Row({ label, value }: { label: string; value: string | null | undefined }) {
  return (
    <div className="flex justify-between gap-4 border-b border-primary/5 py-2">
      <dt className="text-muted">{label}</dt>
      <dd className="text-right font-medium text-primary">{value ?? "—"}</dd>
    </div>
  );
}
