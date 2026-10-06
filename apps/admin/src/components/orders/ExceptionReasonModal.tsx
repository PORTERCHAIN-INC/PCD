"use client";

import { useEffect, useState } from "react";
import { Button, Modal, Select } from "@/components/crm/primitives";
import { BOARD_LABELS } from "@/lib/operations";

export const EXCEPTION_COLUMNS = [
  { value: "failed", label: "Failed delivery" },
  { value: "returned", label: "Return to sender" },
  { value: "lost", label: "Lost" },
  { value: "damaged", label: "Damaged" },
] as const;

export type ExceptionColumn = (typeof EXCEPTION_COLUMNS)[number]["value"];

export function isExceptionColumn(key: string): key is ExceptionColumn {
  return EXCEPTION_COLUMNS.some((c) => c.value === key);
}

type Props = {
  open: boolean;
  trackingNumber?: string | null;
  /** Pre-selected column when opened from board drop */
  initialColumn?: ExceptionColumn | "";
  allowColumnChange?: boolean;
  onClose: () => void;
  onConfirm: (column: ExceptionColumn, reason: string) => Promise<void>;
};

export function ExceptionReasonModal({
  open,
  trackingNumber,
  initialColumn = "",
  allowColumnChange = true,
  onClose,
  onConfirm,
}: Props) {
  const [column, setColumn] = useState<ExceptionColumn | "">(initialColumn);
  const [reason, setReason] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!open) return;
    setColumn(initialColumn);
    setReason("");
    setError(null);
    setBusy(false);
  }, [open, initialColumn]);

  async function submit() {
    if (!column) {
      setError("Choose an exception type");
      return;
    }
    const note = reason.trim();
    if (note.length < 3) {
      setError("Enter a reason (at least 3 characters)");
      return;
    }
    setBusy(true);
    setError(null);
    try {
      await onConfirm(column, note);
      onClose();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Could not mark exception");
    } finally {
      setBusy(false);
    }
  }

  const label = column ? (BOARD_LABELS[column] ?? column) : "Exception";

  return (
    <Modal
      open={open}
      onClose={onClose}
      title={`Mark ${label}`}
      footer={
        <>
          <Button variant="outline" onClick={onClose} disabled={busy}>
            Cancel
          </Button>
          <Button variant="danger" onClick={() => void submit()} disabled={busy}>
            {busy ? "Saving…" : "Confirm exception"}
          </Button>
        </>
      }
    >
      <div className="space-y-3">
        <p className="text-sm text-muted">
          {trackingNumber ? (
            <>
              Order <span className="font-mono font-medium text-primary">{trackingNumber}</span>
              {" — "}
            </>
          ) : null}
          Exceptions are PorterChain commercial actions. Execution (accept → deliver) stays in the
          driver app.
        </p>
        {allowColumnChange ? (
          <div>
            <label className="mb-1 block text-xs font-semibold uppercase tracking-wide text-muted">
              Exception type
            </label>
            <Select
              value={column}
              onChange={(e) => setColumn(e.target.value as ExceptionColumn | "")}
            >
              <option value="">Select…</option>
              {EXCEPTION_COLUMNS.map((c) => (
                <option key={c.value} value={c.value}>
                  {c.label}
                </option>
              ))}
            </Select>
          </div>
        ) : (
          <p className="text-sm font-medium text-primary">{label}</p>
        )}
        <div>
          <label className="mb-1 block text-xs font-semibold uppercase tracking-wide text-muted">
            Reason (required)
          </label>
          <textarea
            value={reason}
            onChange={(e) => setReason(e.target.value)}
            rows={4}
            placeholder="What happened? Customer unavailable, wrong address, damaged packaging…"
            className="w-full rounded-xl border border-primary/15 bg-white px-3 py-2 text-sm text-primary outline-none focus:border-secondary"
          />
        </div>
        {error && <p className="text-sm text-red-600">{error}</p>}
      </div>
    </Modal>
  );
}
