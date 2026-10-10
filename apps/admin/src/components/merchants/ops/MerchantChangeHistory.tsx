"use client";

import { useState } from "react";
import { History } from "lucide-react";
import { useApiData } from "@/hooks/useApiData";
import { merchantOps } from "@/lib/merchant-ops";
import { dateTime, titleCase } from "@/lib/crmFormat";
import { Empty, Panel, SkeletonRows } from "./ui";

function show(v: unknown): string {
  if (v === null || v === undefined || v === "") return "—";
  if (typeof v === "object") return JSON.stringify(v).slice(0, 80);
  return String(v);
}

/** Who changed prices, contracts, credit, keys, owner or documents: old → new. */
export function MerchantChangeHistory({ id, version = 0 }: { id: string; version?: number }) {
  const { data, error } = useApiData((t) => merchantOps.history(t, id), [id, version], {
    key: `merchant-history-${id}`,
  });
  const [n, setN] = useState(8);
  const rows = data ?? [];
  return (
    <Panel title="Change history">
      {!data && !error ? (
        <SkeletonRows rows={3} label="Loading change history" />
      ) : error ? (
        <Empty title="Couldn't load history" hint={error} />
      ) : rows.length === 0 ? (
        <Empty
          icon={<History className="h-6 w-6" aria-hidden />}
          title="No changes yet"
          hint="Price, contract, credit, key, owner and document changes land here."
        />
      ) : (
        <>
          <ol className="-my-2 divide-y divide-primary/5">
            {rows.slice(0, n).map((r) => (
              <li key={r.id} className="py-3">
                <div className="flex flex-wrap items-baseline justify-between gap-x-3 gap-y-0.5">
                  <p className="text-sm font-bold text-primary">
                    {titleCase(r.area)} ·{" "}
                    {r.action.split(".").slice(1).join(" ").replace(/_/g, " ")}
                  </p>
                  <p className="text-xs text-slate-600">
                    {r.actor ?? "system"}
                    {r.actor_role ? ` · ${titleCase(r.actor_role)}` : ""} · {dateTime(r.at)}
                  </p>
                </div>
                {r.reason && <p className="text-xs text-slate-600">“{r.reason}”</p>}
                <ul className="mt-1 space-y-0.5">
                  {Object.entries(r.changes)
                    .slice(0, 6)
                    .map(([k, c]) => (
                      <li key={k} className="text-xs break-words text-primary">
                        <span className="text-slate-600">{k}</span> {show(c.old)} →{" "}
                        <strong>{show(c.new)}</strong>
                      </li>
                    ))}
                </ul>
              </li>
            ))}
          </ol>
          {rows.length > n ? (
            <button
              onClick={() => setN((x) => x + 20)}
              className="mt-3 min-h-11 rounded-full px-3 text-sm font-semibold text-secondary hover:bg-secondary/5"
            >
              Show {Math.min(20, rows.length - n)} more
            </button>
          ) : null}
        </>
      )}
    </Panel>
  );
}
