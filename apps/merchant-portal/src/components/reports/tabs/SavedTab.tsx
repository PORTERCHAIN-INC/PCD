"use client";

import { useState } from "react";
import Button from "@/components/ui/Button";
import { REPORT_TYPES, reportsApi, type SavedReport } from "@/lib/reports";

export function SavedTab({
  saved,
  onOpen,
  onRefresh,
  getToken,
  orgId,
}: {
  saved: SavedReport[];
  onOpen: (reportType: string) => void;
  onRefresh: () => Promise<void>;
  getToken: () => Promise<string>;
  orgId?: string;
}) {
  const [name, setName] = useState("");
  const [reportType, setReportType] = useState("orders");

  const handleSave = async () => {
    if (!name.trim()) return;
    const token = await getToken();
    await reportsApi.saveReport(token, { name, report_type: reportType }, orgId);
    setName("");
    await onRefresh();
  };

  const handleDelete = async (id: string) => {
    const token = await getToken();
    await reportsApi.deleteSaved(token, id, orgId);
    await onRefresh();
  };

  return (
    <div className="space-y-6">
      <section className="rounded-2xl border border-primary/10 bg-white p-6">
        <h2 className="font-semibold text-primary">Save a report shortcut</h2>
        <p className="mt-1 text-sm text-muted">Opens that report. It does not email anyone.</p>
        <div className="mt-4 flex flex-wrap gap-3">
          <input
            className="rounded-lg border border-primary/20 px-3 py-2 text-sm"
            placeholder="Report name"
            value={name}
            onChange={(e) => setName(e.target.value)}
          />
          <select
            className="rounded-lg border border-primary/20 px-3 py-2 text-sm"
            value={reportType}
            onChange={(e) => setReportType(e.target.value)}
          >
            {REPORT_TYPES.map((t) => (
              <option key={t.id} value={t.id}>
                {t.label}
              </option>
            ))}
          </select>
          <Button size="sm" onClick={() => void handleSave()}>
            Save report
          </Button>
        </div>
      </section>
      <section className="rounded-2xl border border-primary/10 bg-white p-6">
        <h2 className="font-semibold text-primary">Saved reports</h2>
        <ul className="mt-4 space-y-2 text-sm">
          {saved.length === 0 && <li className="text-muted">No saved reports</li>}
          {saved.map((r) => (
            <li key={r.id} className="flex items-center justify-between gap-4">
              <button
                type="button"
                className="text-left text-secondary hover:underline"
                onClick={() => onOpen(r.report_type)}
              >
                <span className="font-medium">{r.name}</span>
                <span className="ml-2 text-muted">({r.report_type})</span>
              </button>
              <Button variant="outline" size="sm" onClick={() => void handleDelete(r.id)}>
                Remove
              </Button>
            </li>
          ))}
        </ul>
      </section>
    </div>
  );
}
