"use client";

import { useCallback, useEffect, useState } from "react";
import { RotateCcw, Search } from "lucide-react";
import { useAdminAuth } from "@/hooks/useAdminAuth";
import {
  confirmMatches,
  daysLeft,
  deletedItemsApi,
  type DeletedItem,
  type DeletedMeta,
} from "@/lib/deleted-items";

/** Settings > Deleted items. Restore anything; super admins can delete permanently. */
export default function DeletedItemsPanel() {
  const { getApiToken } = useAdminAuth();
  const [meta, setMeta] = useState<DeletedMeta | null>(null);
  const [items, setItems] = useState<DeletedItem[]>([]);
  const [entity, setEntity] = useState("");
  const [q, setQ] = useState("");
  const [msg, setMsg] = useState<string | null>(null);
  const [purging, setPurging] = useState<DeletedItem | null>(null);
  const [typed, setTyped] = useState("");
  const [days, setDays] = useState<number | "">("");

  const load = useCallback(async () => {
    try {
      const t = await getApiToken();
      const [m, l] = await Promise.all([
        deletedItemsApi.meta(t),
        deletedItemsApi.list(t, { entity, q }),
      ]);
      setMeta(m);
      setItems(l.items);
      setDays((d) => (d === "" ? m.retention_days : d));
    } catch (e) {
      setMsg(e instanceof Error ? e.message : "Could not load deleted items");
    }
  }, [getApiToken, entity, q]);

  useEffect(() => {
    void load();
  }, [load]);

  async function act(fn: (t: string) => Promise<unknown>, ok: string) {
    setMsg(null);
    try {
      await fn(await getApiToken());
      setMsg(ok);
      setPurging(null);
      setTyped("");
      await load();
    } catch (e) {
      setMsg(e instanceof Error ? e.message : "Failed");
    }
  }

  return (
    <div className="rounded-xl bg-[#0A1428] p-5 text-slate-200" data-testid="deleted-items">
      <div className="flex flex-wrap items-center gap-2">
        <div className="relative flex-1 min-w-48">
          <Search className="absolute left-2.5 top-2 h-3.5 w-3.5 text-slate-500" />
          <input
            value={q}
            onChange={(e) => setQ(e.target.value)}
            placeholder="Search deleted items"
            className="w-full rounded-md border border-white/10 bg-white/5 py-1.5 pl-8 pr-2 text-xs text-white placeholder:text-slate-500 focus:border-[#4F8CFF] focus:outline-none"
          />
        </div>
        <select
          value={entity}
          onChange={(e) => setEntity(e.target.value)}
          className="rounded-md border border-white/10 bg-white/5 px-2 py-1.5 text-xs text-white"
        >
          <option value="">All types</option>
          {meta?.entities.map((e) => (
            <option key={e.key} value={e.key}>
              {e.title}
            </option>
          ))}
        </select>
        <span className="ml-auto flex items-center gap-1.5 text-xs text-slate-400">
          Auto-delete after
          <input
            type="number"
            min={1}
            max={3650}
            value={days}
            disabled={!meta?.can_purge}
            onChange={(e) => setDays(e.target.value === "" ? "" : Number(e.target.value))}
            className="w-14 rounded-md border border-white/10 bg-white/5 px-1.5 py-1 text-right text-xs text-white disabled:opacity-50"
          />
          days
          {meta?.can_purge && days !== meta.retention_days && days !== "" && (
            <button
              type="button"
              onClick={() => act((t) => deletedItemsApi.setRetention(t, Number(days)), "Saved")}
              className="rounded-md bg-[#4F8CFF] px-2 py-1 text-xs font-medium text-white"
            >
              Save
            </button>
          )}
        </span>
      </div>

      {msg && (
        <p className="mt-3 text-xs text-slate-300" data-testid="deleted-items-msg">
          {msg}
        </p>
      )}

      <table className="mt-4 w-full text-left text-xs">
        <thead className="text-[10px] uppercase tracking-wider text-slate-500">
          <tr>
            <th className="py-2 font-medium">Item</th>
            <th className="font-medium">Type</th>
            <th className="font-medium">Deleted by</th>
            <th className="font-medium">When</th>
            <th className="font-medium">Auto-delete</th>
            <th />
          </tr>
        </thead>
        <tbody className="divide-y divide-white/5">
          {items.length === 0 && (
            <tr>
              <td colSpan={6} className="py-10 text-center text-slate-500">
                Nothing deleted.
              </td>
            </tr>
          )}
          {items.map((it) => {
            const left = daysLeft(it.purge_after);
            return (
              <tr key={it.id} className="hover:bg-white/[0.02]">
                <td className="py-2.5">
                  <span className="text-white">{it.label}</span>
                  {it.children > 0 && <span className="ml-1.5 text-slate-500">+{it.children}</span>}
                  {it.reason && <div className="text-[11px] text-slate-500">{it.reason}</div>}
                </td>
                <td className="text-slate-400">{it.entity_title}</td>
                <td className="text-slate-400">{it.deleted_by ?? "—"}</td>
                <td className="text-slate-400">
                  {it.deleted_at ? new Date(it.deleted_at).toLocaleString() : "—"}
                </td>
                <td className="text-slate-400">
                  {left === null ? (it.outcome?.reason ? "Archive only" : "—") : `${left}d`}
                </td>
                <td className="py-2 text-right">
                  <button
                    type="button"
                    data-testid="restore"
                    onClick={() =>
                      act((t) => deletedItemsApi.restore(t, it.id), `Restored ${it.label}`)
                    }
                    className="inline-flex items-center gap-1 rounded-md px-2 py-1 text-[#4F8CFF] hover:bg-[#4F8CFF]/10"
                  >
                    <RotateCcw className="h-3 w-3" /> Restore
                  </button>
                  {meta?.can_purge && (
                    <button
                      type="button"
                      data-testid="purge"
                      onClick={() => {
                        setPurging(it);
                        setTyped("");
                      }}
                      className="ml-1 rounded-md px-2 py-1 text-slate-500 hover:text-white"
                    >
                      Delete forever
                    </button>
                  )}
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>

      {purging && (
        <div
          className="fixed inset-0 z-50 flex items-center justify-center bg-black/60"
          role="dialog"
        >
          <div className="w-[26rem] rounded-xl border border-white/10 bg-[#0B1530] p-5 text-sm text-slate-200 shadow-2xl">
            <p className="font-medium text-white">Delete forever?</p>
            <p className="mt-1 text-xs text-slate-400">
              {purging.entity === "customer"
                ? "Personal data is erased (PIPEDA). Orders, invoices and payments are kept for tax records."
                : "This can't be undone. Records the law keeps (invoices, payments, delivered parcels) stay archived."}
            </p>
            <p className="mt-3 text-xs text-slate-400">
              Type <span className="font-mono text-white">{purging.label}</span> to confirm.
            </p>
            <input
              autoFocus
              value={typed}
              onChange={(e) => setTyped(e.target.value)}
              data-testid="purge-confirm-input"
              className="mt-2 w-full rounded-md border border-white/10 bg-white/5 px-2 py-1.5 font-mono text-xs text-white focus:border-[#4F8CFF] focus:outline-none"
            />
            <div className="mt-4 flex justify-end gap-2">
              <button
                type="button"
                onClick={() => setPurging(null)}
                className="px-2.5 py-1 text-xs text-slate-400 hover:text-white"
              >
                Cancel
              </button>
              <button
                type="button"
                disabled={!confirmMatches(typed, purging.label)}
                data-testid="purge-confirm"
                onClick={() =>
                  act(
                    (t) => deletedItemsApi.purge(t, purging.id, typed),
                    `Deleted ${purging.label} forever`
                  )
                }
                className="rounded-md bg-[#4F8CFF] px-3 py-1 text-xs font-medium text-white disabled:opacity-30"
              >
                Delete forever
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
