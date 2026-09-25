"use client";

import { useCallback, useEffect, useState } from "react";
import Button from "@/components/ui/Button";
import { settingsApi, type PrivacyStatus } from "@/lib/settings";
import { formatDate } from "@/lib/utils";

export function PrivacyTab({
  getToken,
  orgId,
}: {
  getToken: () => Promise<string>;
  orgId?: string;
}) {
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [reason, setReason] = useState("");
  const [privacy, setPrivacy] = useState<PrivacyStatus | null>(null);

  const loadPrivacy = useCallback(async () => {
    const token = await getToken();
    const status = await settingsApi.privacyStatus(token, orgId);
    setPrivacy(status);
  }, [getToken, orgId]);

  useEffect(() => {
    void loadPrivacy().catch((e) => {
      setError(e instanceof Error ? e.message : "Could not load privacy status");
    });
  }, [loadPrivacy]);

  const downloadExport = async () => {
    setBusy(true);
    setMessage(null);
    setError(null);
    try {
      const token = await getToken();
      const payload = await settingsApi.exportPrivacy(token, orgId);
      const blob = new Blob([JSON.stringify(payload, null, 2)], { type: "application/json" });
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = "porterchain-company-export.json";
      a.click();
      URL.revokeObjectURL(url);
      setMessage("Export downloaded.");
    } catch (e) {
      setError(e instanceof Error ? e.message : "Export failed");
    } finally {
      setBusy(false);
    }
  };

  const requestDelete = async () => {
    if (
      !window.confirm(
        "Request deletion of this company file? PorterChain will review for 30 days. Live orders and unpaid invoices are not removed automatically."
      )
    ) {
      return;
    }
    setBusy(true);
    setMessage(null);
    setError(null);
    try {
      const token = await getToken();
      const result = await settingsApi.requestDeletion(token, reason || undefined, orgId);
      setMessage(`${result.message} Reference: ${result.reference}`);
      setReason("");
      await loadPrivacy();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Request failed");
    } finally {
      setBusy(false);
    }
  };

  const pending = privacy?.status === "pending";
  const erased = privacy?.status === "erased";
  const locked = pending || erased;

  return (
    <section className="space-y-4 rounded-2xl border border-primary/10 bg-white p-6">
      <h2 className="font-semibold text-primary">Privacy</h2>
      <p className="text-sm text-muted">
        {privacy?.message ||
          "Download a copy of this company’s file, or ask PorterChain to delete it. Live orders and unpaid invoices are not wiped automatically."}
      </p>
      {pending && privacy?.delete_reference ? (
        <p className="rounded-xl border border-amber-200 bg-amber-50 px-4 py-3 text-sm text-amber-900">
          Request pending. Reference{" "}
          <span className="font-mono font-semibold">{privacy.delete_reference}</span>
          {privacy.sla_days ? ` · Review within ${privacy.sla_days} days` : ""}
        </p>
      ) : null}
      {erased ? (
        <p className="rounded-xl border border-primary/10 bg-gray-bg px-4 py-3 text-sm text-primary">
          Contact details were removed. Order numbers and invoice amounts stay on file.
        </p>
      ) : null}
      <Button size="sm" disabled={busy} onClick={() => void downloadExport()}>
        Download company export
      </Button>
      <div className="space-y-2">
        <label className="text-sm font-medium">Deletion request</label>
        <textarea
          className="w-full rounded-lg border border-primary/15 px-3 py-2 text-sm"
          rows={3}
          value={reason}
          onChange={(e) => setReason(e.target.value)}
          placeholder="Optional reason"
          disabled={locked || busy}
        />
        <Button size="sm" disabled={busy || locked} onClick={() => void requestDelete()}>
          {pending ? "Request already submitted" : erased ? "Already erased" : "Request deletion"}
        </Button>
      </div>
      {message && <p className="text-sm text-primary">{message}</p>}
      {error && <p className="text-sm text-red-600">{error}</p>}
      {(privacy?.recent_logs?.length ?? 0) > 0 ? (
        <div className="border-t border-primary/10 pt-4">
          <h3 className="text-sm font-semibold text-primary">Company activity</h3>
          <ul className="mt-2 space-y-2 text-sm">
            {privacy?.recent_logs?.slice(0, 20).map((row) => (
              <li
                key={row.id}
                className="flex justify-between gap-4 border-b border-primary/5 py-2"
              >
                <span className="font-medium text-primary">{row.summary}</span>
                <span className="shrink-0 text-xs text-muted">
                  {row.created_at ? formatDate(row.created_at) : "—"}
                </span>
              </li>
            ))}
          </ul>
        </div>
      ) : null}
    </section>
  );
}
