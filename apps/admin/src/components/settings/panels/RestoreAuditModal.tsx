"use client";

import { useState } from "react";
import { Button, Field, Modal } from "@/components/crm/primitives";
import { useAdminAuth } from "@/hooks/useAdminAuth";
import { settingsApi, type AuditEntry } from "@/lib/settings";
import { withStaffStepUp } from "@/lib/staff-step-up";

export function RestoreAuditModal({
  log,
  open,
  onClose,
  onRestored,
}: {
  log: AuditEntry | null;
  open: boolean;
  onClose: () => void;
  onRestored: () => void;
}) {
  const { getApiToken } = useAdminAuth();
  const [reason, setReason] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  function handleClose() {
    setReason("");
    setError(null);
    setBusy(false);
    onClose();
  }

  async function applyRestore() {
    const auditId = log?.id;
    if (!auditId) return;
    if (!reason.trim()) {
      setError("A rollback reason is required");
      return;
    }
    setBusy(true);
    setError(null);
    try {
      const token = await getApiToken();
      await withStaffStepUp(token, () => settingsApi.restoreAudit(token, auditId, reason.trim()));
      setReason("");
      onRestored();
      onClose();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Restore failed");
    } finally {
      setBusy(false);
    }
  }

  const defaultHint = log?.resource_id ? `Rollback ${log.resource_id}` : "Rollback prior value";

  return (
    <Modal
      open={open}
      onClose={handleClose}
      title="Restore previous value"
      panelClassName="max-w-lg"
      footer={
        <>
          <Button variant="outline" onClick={handleClose} disabled={busy}>
            Cancel
          </Button>
          <Button disabled={busy || !reason.trim()} onClick={() => void applyRestore()}>
            {busy ? "Restoring…" : "Restore"}
          </Button>
        </>
      }
    >
      <div className="space-y-4">
        <p className="text-sm text-primary/80">
          This writes the prior value for{" "}
          <span className="font-mono text-xs">{log?.resource_id || "this key"}</span> and appends a
          new audit row. Provide a reason for the rollback.
        </p>
        <Field label="Reason">
          <input
            className="w-full rounded-lg border border-primary/15 bg-white px-3 py-2 text-sm"
            value={reason}
            placeholder={defaultHint}
            onChange={(e) => setReason(e.target.value)}
            disabled={busy}
            autoFocus
          />
        </Field>
        {error && <p className="text-xs text-red-600">{error}</p>}
      </div>
    </Modal>
  );
}
