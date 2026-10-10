"use client";

import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { Button } from "@/components/crm/primitives";
import { api } from "@/lib/api";
import { LEAD_PRIORITIES, LEAD_STATUSES, leadsApi } from "@/lib/leads";

type Staff = { id: string; label: string };

function toStaff(rows: Array<Record<string, unknown>>): Staff[] {
  return rows
    .filter((r) => typeof r.id === "string" && r.is_active !== false)
    .map((r) => ({
      id: String(r.id),
      label: String(r.name || r.email || r.id),
    }));
}

/** Bulk assign / status / priority + export for the selected rows. */
export default function LeadBulkBar({
  selected,
  getToken,
  onDone,
  onClear,
  onExportSelected,
}: {
  selected: string[];
  getToken: () => Promise<string>;
  onDone: () => void;
  onClear: () => void;
  onExportSelected: () => void;
}) {
  const [assignee, setAssignee] = useState("");
  const [status, setStatus] = useState("");
  const [priority, setPriority] = useState("");
  const [busy, setBusy] = useState(false);
  const [msg, setMsg] = useState<string | null>(null);

  const { data: staff = [] } = useQuery({
    queryKey: ["lead-assignees"],
    queryFn: async () => toStaff(await api.staff(await getToken())),
    retry: false,
    staleTime: 5 * 60_000,
  });

  if (selected.length === 0) return null;

  const apply = async () => {
    if (!assignee && !status && !priority) return;
    setBusy(true);
    setMsg(null);
    try {
      const out = await leadsApi.bulkUpdate(await getToken(), {
        lead_ids: selected,
        ...(assignee === "__none__"
          ? { unassign: true }
          : assignee
            ? { assigned_to: assignee }
            : {}),
        ...(status ? { status } : {}),
        ...(priority ? { priority } : {}),
      });
      setMsg(`Updated ${out.updated} lead${out.updated === 1 ? "" : "s"}.`);
      setAssignee("");
      setStatus("");
      setPriority("");
      onDone();
    } catch (e) {
      setMsg(e instanceof Error ? e.message : "Bulk update failed");
    } finally {
      setBusy(false);
    }
  };

  const select = "rounded-lg border border-primary/10 bg-white px-2 py-1.5 text-sm";
  return (
    <div
      className="sticky top-0 z-10 mb-3 flex flex-wrap items-center gap-2 rounded-xl border border-secondary/30 bg-secondary/5 p-3"
      role="region"
      aria-label="Bulk actions"
    >
      <span className="text-sm font-medium text-primary">{selected.length} selected</span>
      <select
        className={select}
        value={assignee}
        onChange={(e) => setAssignee(e.target.value)}
        aria-label="Assign to"
      >
        <option value="">Assign to…</option>
        <option value="__none__">Unassign</option>
        {staff.map((s) => (
          <option key={s.id} value={s.id}>
            {s.label}
          </option>
        ))}
      </select>
      <select
        className={select}
        value={status}
        onChange={(e) => setStatus(e.target.value)}
        aria-label="Set status"
      >
        <option value="">Status…</option>
        {LEAD_STATUSES.map((s) => (
          <option key={s} value={s}>
            {s}
          </option>
        ))}
      </select>
      <select
        className={select}
        value={priority}
        onChange={(e) => setPriority(e.target.value)}
        aria-label="Set priority"
      >
        <option value="">Priority…</option>
        {LEAD_PRIORITIES.map((p) => (
          <option key={p} value={p}>
            {p}
          </option>
        ))}
      </select>
      <Button onClick={() => void apply()} disabled={busy || (!assignee && !status && !priority)}>
        {busy ? "Applying…" : "Apply"}
      </Button>
      <Button variant="outline" onClick={onExportSelected}>
        Export selected
      </Button>
      <Button variant="ghost" onClick={onClear}>
        Clear
      </Button>
      {msg ? (
        <span className="text-xs text-muted" role="status">
          {msg}
        </span>
      ) : null}
    </div>
  );
}
