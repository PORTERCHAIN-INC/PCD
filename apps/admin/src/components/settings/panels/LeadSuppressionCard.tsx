"use client";

import { useState } from "react";
import { useApiData } from "@/hooks/useApiData";
import { hasPermission, useOptionalSessionContext } from "@porterchain/auth";
import { useAdminProfile } from "@/components/nav/AdminProfileContext";
import { leadsApi } from "@/lib/leads";
import { PageSkeleton } from "@porterchain/ui/loading";
import { SettingsCard } from "../ui/SettingsPrimitives";

/** Hashed DNC list — no raw email/phone. Clear requires system:all. */
export function LeadSuppressionCard() {
  const { profile } = useAdminProfile();
  const session = useOptionalSessionContext()?.session;
  const canClear =
    hasPermission(session?.permissions, "system:all") || profile?.role === "super_admin";
  const [busy, setBusy] = useState(false);
  const [actionError, setActionError] = useState("");
  const {
    data: page,
    error,
    refetch,
    getApiToken,
    loading,
  } = useApiData((t) => leadsApi.listSuppressions(t, { limit: 50 }), [], {
    key: "lead-suppressions",
  });
  const rows = page?.items ?? [];
  const total = page?.total ?? 0;
  const showError = actionError || error;

  return (
    <SettingsCard title="Do-not-contact suppressions">
      <p className="mb-3 text-xs text-muted">
        Hashed email/phone only (CASL / GDPR object). Re-opt-in clears via fresh form consent; staff
        clear is super-admin only.
      </p>
      {showError ? <p className="mb-2 text-sm text-red-600">{showError}</p> : null}
      {loading && !page ? (
        <PageSkeleton rows={2} />
      ) : (
        <>
          <p className="mb-2 text-xs text-muted">
            {total} row{total === 1 ? "" : "s"}
          </p>
          {rows.length === 0 ? (
            <p className="text-sm text-muted">No suppressions yet.</p>
          ) : (
            <ul
              className="max-h-64 space-y-2 overflow-y-auto text-sm"
              aria-label="Suppression list"
            >
              {rows.map((r) => (
                <li
                  key={r.id}
                  className="flex flex-wrap items-center justify-between gap-2 rounded-lg border border-primary/10 px-3 py-2"
                >
                  <div>
                    <span className="font-medium capitalize">{r.hash_kind}</span>
                    <span className="ml-2 font-mono text-xs text-muted">
                      {r.value_hash.slice(0, 12)}…
                    </span>
                    <p className="text-xs text-muted">
                      {r.source}
                      {r.created_at ? ` · ${r.created_at}` : ""}
                    </p>
                  </div>
                  {canClear ? (
                    <button
                      type="button"
                      disabled={busy}
                      className="rounded-lg border border-primary/15 px-2 py-1 text-xs disabled:opacity-50"
                      aria-label={`Clear suppression ${r.id}`}
                      onClick={() => {
                        if (!window.confirm("Clear this suppression hash?")) return;
                        void (async () => {
                          setBusy(true);
                          setActionError("");
                          try {
                            await leadsApi.deleteSuppression(await getApiToken(), r.id);
                            await refetch();
                          } catch (err) {
                            setActionError(err instanceof Error ? err.message : "Clear failed");
                          } finally {
                            setBusy(false);
                          }
                        })();
                      }}
                    >
                      Clear
                    </button>
                  ) : null}
                </li>
              ))}
            </ul>
          )}
        </>
      )}
      <button
        type="button"
        className="mt-3 text-xs font-medium text-secondary hover:underline"
        onClick={() => void refetch()}
      >
        Refresh list
      </button>
    </SettingsCard>
  );
}
