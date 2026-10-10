"use client";

import { useEffect, useState } from "react";
import { useApiData } from "@/hooks/useApiData";
import { useAdminAuth } from "@/hooks/useAdminAuth";
import { dispatch, type Retention, type RetentionRun } from "@/lib/dispatch";

const NUM = "w-full min-w-0 rounded-lg border border-primary/15 bg-white px-2 py-1.5 text-sm tabular-nums text-primary";

export function RetentionCard({ tick }: { tick: number }) {
  const { getApiToken } = useAdminAuth();
  const { data } = useApiData((t) => dispatch.retention(t), [tick], { key: "dispatch-retention" });
  const [draft, setDraft] = useState<Retention | null>(null);
  const [run, setRun] = useState<RetentionRun | null>(null);
  const [msg, setMsg] = useState<string | null>(null);

  useEffect(() => {
    if (data) setDraft(data);
  }, [data]);
  if (!draft) return null;

  const act = async (fn: (t: string) => Promise<unknown>, done: string) => {
    setMsg("Working…");
    try {
      await fn(await getApiToken());
      setMsg(done);
    } catch (e) {
      setMsg(e instanceof Error ? e.message : "Failed");
    }
  };

  return (
    <section className="rounded-2xl border border-primary/10 bg-white p-4" data-testid="dispatch-retention">
      <h2 className="text-base font-semibold text-primary">Data retention</h2>
      <p className="text-xs text-muted">
        GPS breadcrumbs are deleted after the limit. Proof-of-delivery references are redacted after the claims window.
        Runs daily.
      </p>
      <div className="mt-3 grid grid-cols-2 gap-3 sm:grid-cols-4">
        <label className="text-xs text-muted">
          GPS days (7–365)
          <input
            className={NUM}
            type="number"
            min={7}
            max={365}
            value={draft.gps_days}
            onChange={(e) => setDraft({ ...draft, gps_days: Number(e.target.value) })}
          />
        </label>
        <label className="text-xs text-muted">
          POD days (90–2555)
          <input
            className={NUM}
            type="number"
            min={90}
            max={2555}
            value={draft.pod_days}
            onChange={(e) => setDraft({ ...draft, pod_days: Number(e.target.value) })}
          />
        </label>
        <label className="flex items-end gap-2 text-xs text-muted">
          <input type="checkbox" checked={draft.enabled} onChange={(e) => setDraft({ ...draft, enabled: e.target.checked })} />
          Daily purge on
        </label>
      </div>
      <div className="mt-3 flex flex-wrap items-center gap-2">
        <button
          type="button"
          onClick={() => act((t) => dispatch.saveRetention(t, draft), "Saved")}
          className="min-h-10 rounded-xl px-4 text-sm font-semibold text-white"
          style={{ backgroundColor: "var(--primary)" }}
        >
          Save limits
        </button>
        <button
          type="button"
          onClick={() =>
            act(async (t) => setRun(await dispatch.runRetention(t, true)), "Dry run — nothing deleted")
          }
          className="min-h-10 rounded-xl border border-primary/15 px-3 text-sm font-medium text-primary"
        >
          Preview purge
        </button>
        {msg && <span className="text-sm text-muted">{msg}</span>}
      </div>
      {run && (
        <p className="mt-2 text-sm text-primary" data-testid="retention-preview">
          {run.dry_run ? "Preview: " : "Purged: "}
          <b className="tabular-nums">{run.gps_pings}</b> GPS ping(s), <b className="tabular-nums">{run.pod_refs}</b> POD
          reference(s) and <b className="tabular-nums">{run.pod_files ?? 0}</b> photo file(s) (
          {((run.pod_file_bytes ?? 0) / 1_000_000).toFixed(1)} MB) past the limits
          {run.dry_run ? " — nothing deleted." : ` — ${run.pod_files_deleted ?? 0} file(s) deleted.`}
        </p>
      )}
    </section>
  );
}
