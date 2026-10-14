"use client";

import { useState } from "react";
import { Trash2 } from "lucide-react";
import { useAdminAuth } from "@/hooks/useAdminAuth";
import {
  cascadeSummary,
  deletedItemsApi,
  type DeleteCheck,
  type DeletableEntity,
} from "@/lib/deleted-items";

/**
 * One delete button for every admin entity. Soft by default: the item moves to
 * Settings > Deleted items and can be restored. Guards explain why when it can't.
 */
export default function DeleteButton({
  entity,
  id,
  onDeleted,
  compact = false,
}: {
  entity: DeletableEntity;
  id: string;
  onDeleted?: () => void;
  compact?: boolean;
}) {
  const { getApiToken } = useAdminAuth();
  const [check, setCheck] = useState<DeleteCheck | null>(null);
  const [reason, setReason] = useState("");
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<string | null>(null);
  const [done, setDone] = useState(false);
  const [pos, setPos] = useState<{ top: number; right: number } | null>(null);

  async function open(e: React.MouseEvent) {
    e.stopPropagation();
    e.preventDefault();
    // Fixed position so tables/cards with overflow-hidden never clip the dialog.
    const r = e.currentTarget.getBoundingClientRect();
    setPos({ top: r.bottom + 8, right: Math.max(8, window.innerWidth - r.right) });
    setErr(null);
    setBusy(true);
    try {
      setCheck(await deletedItemsApi.check(await getApiToken(), entity, id));
    } catch (x) {
      setErr(x instanceof Error ? x.message : "Check failed");
    } finally {
      setBusy(false);
    }
  }

  async function confirm() {
    setBusy(true);
    setErr(null);
    try {
      await deletedItemsApi.remove(await getApiToken(), entity, id, reason);
      setDone(true);
      setCheck(null);
      onDeleted?.();
    } catch (x) {
      setErr(x instanceof Error ? x.message : "Delete failed");
    } finally {
      setBusy(false);
    }
  }

  if (done) return <span className="text-xs text-slate-400">Moved to Deleted items</span>;

  return (
    <span className="relative inline-block" onClick={(e) => e.stopPropagation()}>
      <button
        type="button"
        onClick={open}
        disabled={busy}
        aria-label="Delete"
        data-testid={`delete-${entity}`}
        className={
          compact
            ? "rounded p-1 text-slate-400 hover:bg-slate-100 hover:text-slate-900 disabled:opacity-40"
            : "inline-flex items-center gap-1.5 rounded-md border border-slate-300 px-2.5 py-1 text-xs font-medium text-slate-700 hover:border-slate-500 hover:text-slate-900 disabled:opacity-40"
        }
      >
        <Trash2 className="h-3.5 w-3.5" />
        {!compact && "Delete"}
      </button>
      {(check || err) && (
        <div
          role="dialog"
          style={pos ? { top: pos.top, right: pos.right } : undefined}
          className="fixed z-50 w-80 rounded-lg border border-white/10 bg-[#0B1530] p-4 text-left text-sm text-slate-200 shadow-2xl"
        >
          {err && <p className="text-[13px] text-slate-200">{err}</p>}
          {check && !check.allowed && (
            <>
              <p className="text-[11px] font-medium uppercase tracking-wider text-slate-500">
                Can&apos;t delete
              </p>
              <p className="mt-1 text-[13px] leading-snug" data-testid="delete-guard">
                {check.reason}
              </p>
            </>
          )}
          {check && check.allowed && (
            <>
              <p className="font-medium text-white">Delete {check.label}?</p>
              <p className="mt-1 text-xs text-slate-400">
                It moves to Settings → Deleted items. You can restore it.
                {Object.keys(check.cascade).length > 0 && (
                  <> Also hides {cascadeSummary(check.cascade)}.</>
                )}
              </p>
              <input
                value={reason}
                onChange={(e) => setReason(e.target.value)}
                placeholder="Reason (optional)"
                className="mt-3 w-full rounded-md border border-white/10 bg-white/5 px-2 py-1.5 text-xs text-white placeholder:text-slate-500 focus:border-[#4F8CFF] focus:outline-none"
              />
            </>
          )}
          <div className="mt-3 flex justify-end gap-2">
            <button
              type="button"
              onClick={() => {
                setCheck(null);
                setErr(null);
              }}
              className="rounded-md px-2.5 py-1 text-xs text-slate-400 hover:text-white"
            >
              {check?.allowed ? "Cancel" : "Close"}
            </button>
            {check?.allowed && (
              <button
                type="button"
                onClick={confirm}
                disabled={busy}
                data-testid="delete-confirm"
                className="rounded-md bg-[#4F8CFF] px-3 py-1 text-xs font-medium text-white hover:bg-[#3D7BF0] disabled:opacity-50"
              >
                Delete
              </button>
            )}
          </div>
        </div>
      )}
    </span>
  );
}
