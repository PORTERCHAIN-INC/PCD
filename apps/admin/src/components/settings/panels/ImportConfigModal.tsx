"use client";

import { useRef, useState } from "react";
import { Button, Field, Modal, Textarea } from "@/components/crm/primitives";
import { useAdminAuth } from "@/hooks/useAdminAuth";
import { settingsApi } from "@/lib/settings";
import { withStaffStepUp } from "@/lib/staff-step-up";

type Preview = {
  dry_run?: boolean;
  would_write?: number;
  added?: string[];
  changed?: string[];
  blocked?: string[];
};

export function ImportConfigModal({
  open,
  onClose,
  onImported,
}: {
  open: boolean;
  onClose: () => void;
  onImported: () => void;
}) {
  const { getApiToken } = useAdminAuth();
  const fileRef = useRef<HTMLInputElement>(null);
  const [raw, setRaw] = useState("");
  const [reason, setReason] = useState("");
  const [preview, setPreview] = useState<Preview | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  function reset() {
    setRaw("");
    setReason("");
    setPreview(null);
    setError(null);
    setBusy(false);
    if (fileRef.current) fileRef.current.value = "";
  }

  function handleClose() {
    reset();
    onClose();
  }

  function parseConfig(text: string): Record<string, unknown> {
    const parsed = JSON.parse(text) as Record<string, unknown>;
    return ((parsed.config as Record<string, unknown>) ?? parsed) as Record<string, unknown>;
  }

  async function onFile(file: File | undefined) {
    if (!file) return;
    const text = await file.text();
    setRaw(text);
    setPreview(null);
    setError(null);
  }

  async function runDryRun() {
    setBusy(true);
    setError(null);
    setPreview(null);
    try {
      const config = parseConfig(raw);
      const result = await settingsApi.importConfig(await getApiToken(), config, undefined, true);
      setPreview(result);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Dry-run failed — check JSON");
    } finally {
      setBusy(false);
    }
  }

  async function applyImport() {
    if (!reason.trim()) {
      setError("Change reason is required to apply import");
      return;
    }
    setBusy(true);
    setError(null);
    try {
      const config = parseConfig(raw);
      const token = await getApiToken();
      await withStaffStepUp(token, () =>
        settingsApi.importConfig(token, config, reason.trim(), false)
      );
      reset();
      onImported();
      onClose();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Import failed");
    } finally {
      setBusy(false);
    }
  }

  return (
    <Modal
      open={open}
      onClose={handleClose}
      title="Import configuration"
      panelClassName="max-w-2xl"
      footer={
        <>
          <Button variant="outline" onClick={handleClose} disabled={busy}>
            Cancel
          </Button>
          <Button variant="outline" disabled={busy || !raw.trim()} onClick={() => void runDryRun()}>
            {busy && !preview ? "Checking…" : "Dry-run"}
          </Button>
          <Button disabled={busy || !preview || !reason.trim()} onClick={() => void applyImport()}>
            {busy && preview ? "Applying…" : "Apply import"}
          </Button>
        </>
      }
    >
      <div className="space-y-4">
        <p className="text-sm text-primary/80">
          Paste a Settings export JSON or upload a file. Dry-run shows what would change; apply
          writes only Settings-owned keys and audits the reason.
        </p>
        <Field label="JSON file">
          <input
            ref={fileRef}
            type="file"
            accept="application/json,.json"
            className="block w-full text-sm text-primary file:mr-3 file:rounded-lg file:border-0 file:bg-secondary/10 file:px-3 file:py-1.5 file:text-sm file:font-semibold file:text-secondary"
            onChange={(e) => void onFile(e.target.files?.[0])}
          />
        </Field>
        <Field label="Configuration JSON">
          <Textarea
            value={raw}
            onChange={(e) => {
              setRaw(e.target.value);
              setPreview(null);
            }}
            rows={10}
            placeholder='{"config": { "settings_booking": { ... } } }'
            className="font-mono text-xs"
          />
        </Field>
        {preview && (
          <div className="rounded-xl border border-primary/10 bg-gray-bg/40 p-3 text-sm">
            <p className="font-semibold text-primary">
              Dry-run — would write {preview.would_write ?? 0} key(s)
            </p>
            <dl className="mt-2 space-y-1 text-xs text-primary/80">
              <div>
                <dt className="font-medium text-muted">Added</dt>
                <dd className="font-mono break-all">{(preview.added ?? []).join(", ") || "—"}</dd>
              </div>
              <div>
                <dt className="font-medium text-muted">Changed</dt>
                <dd className="font-mono break-all">{(preview.changed ?? []).join(", ") || "—"}</dd>
              </div>
              <div>
                <dt className="font-medium text-muted">Blocked</dt>
                <dd className="font-mono break-all">{(preview.blocked ?? []).join(", ") || "—"}</dd>
              </div>
            </dl>
          </div>
        )}
        <Field label="Change reason (required to apply)">
          <Textarea
            value={reason}
            onChange={(e) => setReason(e.target.value)}
            rows={2}
            placeholder="e.g. Restore GTA rates from staging export"
          />
        </Field>
        {error && <p className="text-sm text-red-600">{error}</p>}
      </div>
    </Modal>
  );
}
